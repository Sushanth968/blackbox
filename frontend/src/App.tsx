import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import InvestigationsPage from './pages/InvestigationsPage'
import InvestigationDetailPage from './pages/InvestigationDetailPage'
import GithubIssuesPage from './pages/GithubIssuesPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/investigations" replace />} />
        <Route path="/investigations" element={<InvestigationsPage />} />
        <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
        <Route path="/github-issues" element={<GithubIssuesPage />} />
      </Routes>
    </Layout>
  )
}
