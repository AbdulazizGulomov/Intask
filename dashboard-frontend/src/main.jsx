import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Apply saved UI preferences globally before first paint (set in Settings → UI Preferences)
const savedTheme = localStorage.getItem('intask_pref_theme') || 'light'
const savedDensity = localStorage.getItem('intask_pref_density') || 'comfortable'
document.documentElement.setAttribute('data-theme', savedTheme)
document.documentElement.setAttribute('data-density', savedDensity)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)