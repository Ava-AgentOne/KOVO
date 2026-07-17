import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Chat from './pages/Chat'
import Tools from './pages/Tools'
import Memory from './pages/Memory'
import Routines from './pages/Routines'
import SkillsAgents from './pages/SkillsAgents'
import Mcp from './pages/Mcp'
import Addons from './pages/Addons'
import Security from './pages/Security'
import Logs from './pages/Logs'
import Heartbeat from './pages/Heartbeat'
import Settings from './pages/Settings'
import Setup from './pages/Setup'
import Login from './pages/Login'

export default function App() {
  return (
    <Routes>
      {/* Setup wizard — full-screen, no sidebar */}
      <Route path="/setup" element={<Setup />} />

      {/* Telegram-approved login — full-screen, no sidebar */}
      <Route path="/login" element={<Login />} />

      {/* Main dashboard — wrapped in Layout */}
      <Route path="*" element={
        <Layout>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/tools" element={<Tools />} />
            <Route path="/memory" element={<Memory />} />
            <Route path="/routines" element={<Routines />} />
            {/* Merged Skills + Agents page (v2.1 IA regroup) */}
            <Route path="/skills" element={<SkillsAgents />} />
            <Route path="/agents" element={<Navigate to="/skills" replace />} />
            {/* Renamed from /mcp so the URL matches the nav label */}
            <Route path="/integrations" element={<Mcp />} />
            <Route path="/mcp" element={<Navigate to="/integrations" replace />} />
            <Route path="/addons" element={<Addons />} />
            <Route path="/security" element={<Security />} />
            <Route path="/heartbeat" element={<Heartbeat />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      } />
    </Routes>
  )
}
