const API = {
  base: "http://localhost:8000",  // FastAPI backend adresi
  manualEntry: "/api/manual_entry",
  uploadImage: "/api/upload/image",
  uploadVideo: "/api/upload/video",
  getRecords: "/api/parking_records",
  createRecord: "/api/parking_records",
  completeRecord: (recordId) => `/api/parking_records/${recordId}/exit`,
};

export default API;
