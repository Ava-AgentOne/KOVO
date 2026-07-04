import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Chat from './pages/Chat'
import Tools from './pages/Tools'
import Agents from './pages/Agents'
import Memory from './pages/Memory'
import Skills from './pages/Skills'
import Mcp from './pages/Mcp'
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
            <Route path="/agents" element={<Agents />} />
            <Route path="/memory" element={<Memory />} />
            <Route path="/skills" element={<Skills />} />
            <Route path="/mcp" element={<Mcp />} />
            {/* Alias — the nav label says "Integrations", deep links must work too */}
            <Route path="/integrations" element={<Navigate to="/mcp" replace />} />
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
