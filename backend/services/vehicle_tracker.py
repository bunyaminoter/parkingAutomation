import argparse
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Optional, Tuple

import cv2
import numpy as np
import requests
from ultralytics import YOLO

from backend.services.plate_recognition import recognize_plate_from_bytes


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger("vehicle-tracker")


DEFAULT_API_BASE = os.getenv("PARKING_API_BASE", "http://localhost:8000")
DEFAULT_LINE_Y = int(os.getenv("VIRTUAL_LINE_Y", "400"))
DEFAULT_MOVEMENT_THRESHOLD = float(os.getenv("MOVEMENT_THRESHOLD", "30.0"))
DEFAULT_DEBOUNCE_SECONDS = float(os.getenv("DEBOUNCE_SECONDS", "10"))
DEFAULT_CAPTURE_DIR = os.getenv("CAPTURE_DIR", "uploads/triggers")
MIN_CONFIDENCE = float(os.getenv("PLATE_MIN_CONFIDENCE", "0.8"))


def perform_ocr(frame: np.ndarray) -> Tuple[Optional[str], float]:
    """Runs OCR pipeline on the given frame. Falls back to dummy plate on failure."""
    try:
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            raise RuntimeError("Frame encode failed")
        plate, confidence = recognize_plate_from_bytes(
            buffer.tobytes(), lang_list=["tr", "en"], gpu=False
        )
        if plate:
            LOGGER.debug("OCR result %s (%.2f)", plate, confidence)
            return plate, confidence
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.warning("OCR failed: %s", exc)
    return None, 0.0


class VehicleTrackerService:
    VEHICLE_CLASS_IDS = {2, 3, 5, 7}  # car, motorcycle, bus, truck (COCO IDs)

    def __init__(
        self,
        camera_index: int = 0,
        weights_path: str = "yolov8n.pt",
        api_base: str = DEFAULT_API_BASE,
        virtual_line_y: int = DEFAULT_LINE_Y,
        movement_threshold: float = DEFAULT_MOVEMENT_THRESHOLD,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        capture_dir: str = DEFAULT_CAPTURE_DIR,
        tracker_config: str = "bytetrack.yaml",
        conf: float = 0.35,
        iou: float = 0.45,
    ):
        self.camera_index = camera_index
        self.api_base = api_base.rstrip("/")
        self.virtual_line_y = virtual_line_y
        self.movement_threshold = movement_threshold
        self.debounce_seconds = debounce_seconds
        self.capture_dir = Path(capture_dir)
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.tracker_config = tracker_config
        self.conf = conf
        self.iou = iou

        LOGGER.info("Loading YOLO weights %s", weights_path)
        self.model = YOLO(weights_path)

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Camera could not be opened")

        self.track_history: Dict[int, Deque[Tuple[int, int]]] = {}
        self.last_positions: Dict[int, Tuple[int, int]] = {}
        self.last_trigger_at: Dict[int, float] = {}
        self.triggered_ids: set[int] = set()

    def run(self):
        LOGGER.info("Vehicle tracker started (camera %s)", self.camera_index)
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    LOGGER.warning("Frame grab failed, exiting")
                    break

                frame = cv2.flip(frame, 1)
                self._process_frame(frame)

                # Draw virtual line
                cv2.line(
                    frame,
                    (0, self.virtual_line_y),
                    (frame.shape[1], self.virtual_line_y),
                    (0, 255, 255),
                    2,
                )

                cv2.imshow("Parking Automation - Vehicle Tracker", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    LOGGER.info("Quit signal received")
                    break
        finally:
            self.cap.release()
            cv2.destroyAllWindows()

    def _process_frame(self, frame: np.ndarray):
        results = self.model.track(
            frame,
            conf=self.conf,
            iou=self.iou,
            imgsz=960,
            tracker=self.tracker_config,
            persist=True,
            verbose=False,
        )
        if not results:
            return

        boxes = results[0].boxes
        if boxes.id is None:
            return

        ids = boxes.id.int().cpu().tolist()
        classes = boxes.cls.int().cpu().tolist()
        xyxy = boxes.xyxy.cpu().numpy()

        for idx, track_id in enumerate(ids):
            if classes[idx] not in self.VEHICLE_CLASS_IDS:
                continue

            box = xyxy[idx]
            cx = int((box[0] + box[2]) / 2)
            cy = int((box[1] + box[3]) / 2)

            self.track_history.setdefault(track_id, deque(maxlen=8)).append((cx, cy))
            movement_ok = self._has_sufficient_movement(track_id)

            prev_pos = self.last_positions.get(track_id)
            self.last_positions[track_id] = (cx, cy)
            crossed = self._has_crossed_line(prev_pos, (cx, cy))

            self._draw_track(frame, box, track_id, movement_ok, crossed)

            if (
                crossed
                and movement_ok
                and self._can_trigger(track_id)
            ):
                LOGGER.info(
                    "Triggering car_id=%s at (%s, %s); movement_ok=%s",
                    track_id,
                    cx,
                    cy,
                    movement_ok,
                )
                self._handle_trigger(frame.copy(), track_id)

    def _draw_track(self, frame, box, track_id, movement_ok, crossed):
        color = (0, 200, 0) if track_id in self.triggered_ids else (255, 0, 0)
        cv2.rectangle(
            frame,
            (int(box[0]), int(box[1])),
            (int(box[2]), int(box[3])),
            color,
            2,
        )
        status = []
        if movement_ok:
            status.append("move")
        if crossed:
            status.append("cross")
        label = f"ID {track_id} {'/'.join(status) if status else ''}"
        cv2.putText(
            frame,
            label,
            (int(box[0]), int(box[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

    def _has_crossed_line(
        self, prev_pos: Optional[Tuple[int, int]], current_pos: Tuple[int, int]
    ) -> bool:
        if prev_pos is None:
            return False
        prev_side = prev_pos[1] < self.virtual_line_y
        curr_side = current_pos[1] < self.virtual_line_y
        return prev_side != curr_side

    def _has_sufficient_movement(self, track_id: int) -> bool:
        history = self.track_history.get(track_id)
        if not history or len(history) < 2:
            return False
        (x0, y0) = history[0]
        (x1, y1) = history[-1]
        distance = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        return distance >= self.movement_threshold

    def _can_trigger(self, track_id: int) -> bool:
        last_time = self.last_trigger_at.get(track_id, 0)
        now = datetime.utcnow().timestamp()
        if track_id in self.triggered_ids and (now - last_time) < self.debounce_seconds:
            return False
        return True

    def _handle_trigger(self, frame: np.ndarray, track_id: int):
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        filename = self.capture_dir / f"car_{track_id}_{timestamp}.jpg"
        cv2.imwrite(str(filename), frame)
        LOGGER.info("Saved trigger frame to %s", filename)

        plate, confidence = perform_ocr(frame)
        if not plate or confidence < MIN_CONFIDENCE:
            LOGGER.info(
                "Skipped posting for car_id=%s; plate=%s confidence=%.2f",
                track_id,
                plate or "UNKNOWN",
                confidence,
            )
            return

        self._post_plate(plate, confidence)
        self.triggered_ids.add(track_id)
        self.last_trigger_at[track_id] = now.timestamp()
        LOGGER.info(
            "Trigger complete car_id=%s plate=%s (conf=%.2f)",
            track_id,
            plate,
            confidence,
        )
 
    def _post_plate(self, plate: str, confidence: float):
        url = f"{self.api_base}/api/manual_entry"
        try:
            response = requests.post(
                url, data={"plate_number": plate, "confidence": confidence}, timeout=5
            )
            if response.status_code >= 400:
                LOGGER.error("FastAPI rejected plate %s: %s", plate, response.text)
            else:
                LOGGER.info("FastAPI accepted plate %s", plate)
        except requests.RequestException as exc:
            LOGGER.error("Failed to POST plate %s: %s", plate, exc)


def parse_args():
    parser = argparse.ArgumentParser(description="Vehicle tracking & plate trigger service")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--weights", type=str, default="yolov8n.pt", help="YOLO weights path")
    parser.add_argument("--api-base", type=str, default=DEFAULT_API_BASE, help="FastAPI base URL")
    parser.add_argument("--line-y", type=int, default=DEFAULT_LINE_Y, help="Virtual line Y")
    parser.add_argument("--movement", type=float, default=DEFAULT_MOVEMENT_THRESHOLD, help="Movement threshold px")
    parser.add_argument("--debounce", type=float, default=DEFAULT_DEBOUNCE_SECONDS, help="Per car debounce seconds")
    parser.add_argument("--tracker-config", type=str, default="bytetrack.yaml", help="Tracker config file")
    parser.add_argument("--capture-dir", type=str, default=DEFAULT_CAPTURE_DIR, help="Capture directory")
    parser.add_argument("--conf", type=float, default=0.35, help="YOLO confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="YOLO IOU threshold")
    return parser.parse_args()


def main():
    args = parse_args()
    service = VehicleTrackerService(
        camera_index=args.camera,
        weights_path=args.weights,
        api_base=args.api_base,
        virtual_line_y=args.line_y,
        movement_threshold=args.movement,
        debounce_seconds=args.debounce,
        tracker_config=args.tracker_config,
        capture_dir=args.capture_dir,
        conf=args.conf,
        iou=args.iou,
    )
    service.run()


if __name__ == "__main__":
    main()

