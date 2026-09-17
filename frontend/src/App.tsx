import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import Dashboard from '@/pages/Dashboard'
import TaskQueue from '@/pages/TaskQueue'
import AgentProcessing from '@/pages/AgentProcessing'
import Execution from '@/pages/Execution'
import HumanReview from '@/pages/HumanReview'
import AuditHistory from '@/pages/AuditHistory'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/queue" element={<TaskQueue />} />
        <Route path="/agent" element={<AgentProcessing />} />
        <Route path="/agent/:jobId" element={<AgentProcessing />} />
        <Route path="/execution" element={<Execution />} />
        <Route path="/execution/:jobId" element={<Execution />} />
        <Route path="/review" element={<HumanReview />} />
        <Route path="/review/:jobId" element={<HumanReview />} />
        <Route path="/history" element={<AuditHistory />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}
