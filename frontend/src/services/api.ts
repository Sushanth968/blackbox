import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export function setApiUser(email: string | null) {
  if (email) {
    api.defaults.headers.common['X-User-Email'] = email
  } else {
    delete api.defaults.headers.common['X-User-Email']
  }
}

// Restore header on page reload from persisted session
try {
  const raw = localStorage.getItem('bb_user')
  const user = raw ? JSON.parse(raw) : null
  if (user?.email) setApiUser(user.email)
} catch { /* ignore */ }
