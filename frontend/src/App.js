import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing";
import Wizard from "./pages/Wizard";
import PlanView from "./pages/PlanView";
import About from "./pages/About";
import Invite from "./pages/Invite";
import AdminDashboard from "./pages/AdminDashboard";
import AdminGate from "./components/AdminGate";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Consumer */}
        <Route path="/" element={<Landing />} />
        <Route path="/plan" element={<Wizard />} />
        <Route path="/plan/:planId" element={<PlanView />} />
        <Route path="/invite/:planId" element={<Invite />} />
        <Route path="/about" element={<About />} />

        {/* Internal / agent console */}
        <Route path="/admin" element={<AdminGate><AdminDashboard /></AdminGate>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
