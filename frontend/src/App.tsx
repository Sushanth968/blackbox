import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import InvestigationsPage from './pages/InvestigationsPage'
import InvestigationDetailPage from './pages/InvestigationDetailPage'
import GithubIssuesPage from './pages/GithubIssuesPage'
import EvidenceLibraryPage from './pages/EvidenceLibraryPage'
import WorkspacesPage from './pages/WorkspacesPage'
import SettingsPage from './pages/SettingsPage'
import HelpPage from './pages/HelpPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route path="/" element={<Navigate to="/investigations" replace />} />
                <Route path="/investigations" element={<InvestigationsPage />} />
                <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
                <Route path="/github-issues" element={<GithubIssuesPage />} />
                <Route path="/evidence" element={<EvidenceLibraryPage />} />
                <Route path="/workspaces" element={<WorkspacesPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/help" element={<HelpPage />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
