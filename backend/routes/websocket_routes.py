"""
WebSocket routes - Real-time updates for parking records
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
from fastapi.encoders import jsonable_encoder

from backend.database import SessionLocal
from backend import models

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        to_remove = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                to_remove.append(connection)
        for connection in to_remove:
            self.disconnect(connection)


manager = ConnectionManager()


def serialize_record(record: models.ParkingRecord):
    return jsonable_encoder(
        {
            "id": record.id,
            "plate_number": record.plate_number,
            "entry_time": record.entry_time,
            "exit_time": record.exit_time,
            "fee": record.fee,
            "confidence": record.confidence,
        }
    )


def get_serialized_records():
    db = SessionLocal()
    try:
        records = db.query(models.ParkingRecord).order_by(models.ParkingRecord.entry_time.desc()).all()
        return [serialize_record(r) for r in records]
    finally:
        db.close()


async def broadcast_latest_records():
    """Tüm bağlı client'lara en son kayıtları gönder"""
    payload = get_serialized_records()
    await manager.broadcast({"type": "records", "payload": payload})


async def send_initial_snapshot(websocket: WebSocket):
    """Yeni bağlanan client'a ilk snapshot'ı gönder"""
    payload = get_serialized_records()
    await websocket.send_json({"type": "records", "payload": payload})


@router.websocket("/ws/parking_records")
async def parking_records_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await send_initial_snapshot(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

