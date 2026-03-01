import { Routes, Route } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import LandingPage from './pages/LandingPage';
import DashboardPage from './pages/DashboardPage';
import BlastRadiusPage from './pages/BlastRadiusPage';
import SmartBlamePage from './pages/SmartBlamePage';
import GovernancePage from './pages/GovernancePage';
import MentorPage from './pages/MentorPage';

export default function App() {
  return (
    <Routes>
      {/* Standalone landing page (no AppShell) */}
      <Route path="/" element={<LandingPage />} />

      {/* Dashboard & app pages wrapped in AppShell */}
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/blast-radius" element={<BlastRadiusPage />} />
        <Route path="/smart-blame" element={<SmartBlamePage />} />
        <Route path="/governance" element={<GovernancePage />} />
        <Route path="/mentor" element={<MentorPage />} />
      </Route>
    </Routes>
  );
}
