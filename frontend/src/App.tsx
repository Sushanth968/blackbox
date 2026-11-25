import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import InvestigationsPage from './pages/InvestigationsPage'
import InvestigationDetailPage from './pages/InvestigationDetailPage'
import GithubIssuesPage from './pages/GithubIssuesPage'
import EvidenceLibraryPage from './pages/EvidenceLibraryPage'
import WorkspacesPage from './pages/WorkspacesPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/investigations" replace />} />
        <Route path="/investigations" element={<InvestigationsPage />} />
        <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
        <Route path="/github-issues" element={<GithubIssuesPage />} />
        <Route path="/evidence" element={<EvidenceLibraryPage />} />
        <Route path="/workspaces" element={<WorkspacesPage />} />
      </Routes>
    </Layout>
  )
}
