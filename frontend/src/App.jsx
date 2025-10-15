import React, { useState } from "react";
import ManualEntryCard from "./components/ManualEntryCard";
import UploadCard from "./components/UploadCard";
import RecordsTable from "./components/RecordsTable";
import "./App.css";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const refresh = () => setRefreshKey((k) => k + 1);

  return (
    <div className="container">
      <h1>Parking Automation</h1>
      <div className="grid">
        <div className="col-6">
          <ManualEntryCard onCreated={refresh} />
        </div>
        <div className="col-6">
          <UploadCard type="image" onCreated={refresh} />
          <div style={{ height: "16px" }}></div>
          <UploadCard type="video" onCreated={refresh} />
        </div>
        <div className="col-12">
          <RecordsTable refreshKey={refreshKey} onRefresh={refresh} />
        </div>
      </div>
    </div>
  );
}
