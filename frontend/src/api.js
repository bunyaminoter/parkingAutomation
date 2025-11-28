const API = {
  base: "http://localhost:8000",  // FastAPI backend adresi
  wsBase: "ws://localhost:8000",
  manualEntry: "/api/manual_entry",
  uploadImage: "/api/upload/image",
  uploadVideo: "/api/upload/video",
  getRecords: "/api/parking_records",
  createRecord: "/api/parking_records",
  completeRecord: (recordId) => `/api/parking_records/${recordId}/exit`,
  recordsStream: "/ws/parking_records",
  login: "/api/login",
  userLogin: "/api/user_login",
  userRecognizePlate: "/api/user/recognize_plate",
};

export default API;
