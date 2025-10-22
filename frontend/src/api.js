const API = {
  base: "http://localhost:8000",  // FastAPI backend adresi
  manualEntry: "/api/manual_entry",
  uploadImage: "/api/upload/image",
  uploadVideo: "/api/upload/video",
  getRecords: "/api/parking_records",
  createRecord: "/api/parking_records",
  completeRecord: (recordId) => `/api/parking_records/${recordId}/exit`,
  login: "/api/login",
  userLogin: "/api/user_login",
  userRecognizePlate: "/api/user/recognize_plate",
};

export default API;
