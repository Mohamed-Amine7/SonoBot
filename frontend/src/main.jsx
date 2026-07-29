import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

function mountSonoBot() {
  // Look for existing mount point, or create one at the end of body
  let mountEl = document.getElementById('sonobot-react-root')
  if (!mountEl) {
    mountEl = document.createElement('div')
    mountEl.id = 'sonobot-react-root'
    document.body.appendChild(mountEl)
  }
  createRoot(mountEl).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

// Wait for DOM to be fully ready before mounting
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountSonoBot)
} else {
  mountSonoBot()
}


