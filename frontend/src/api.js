const API = {
  base: "http://localhost:8000",  // FastAPI backend adresi
  wsBase: "ws://localhost:8000",
  manualEntry: "/api/manual_entry",
  uploadImage: "/api/upload/image",
  uploadVideo: "/api/upload/video",
  getRecords: "/api/parking_records",
  createRecord: "/api/parking_records",
  completeRecord: (recordId) => `/api/parking_records/${recordId}/exit`,
  updatePlate: (recordId) => `/api/parking_records/${recordId}/plate`,
  recordsStream: "/ws/parking_records",
  login: "/api/login",
  superAdminLogin: "/api/super_admin/login",
  userLogin: "/api/user_login",
  userRecognizePlate: "/api/user/recognize_plate",
  listUsers: "/api/users",
  changeUserPassword: (userId) => `/api/users/${userId}/password`,
  createUser: "/api/users",
  updateUser: (userId) => `/api/users/${userId}`,
  deleteUser: (userId) => `/api/users/${userId}`,
};

export default API;
