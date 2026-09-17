import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import * as Sentry from '@sentry/react'

// ─── Sentry Error Monitoring — AURA Frontend ───────────────────────────────
// Automatically captures: JS crashes, React errors, failed API calls, performance
// Get your DSN from: sentry.io → Projects → aura-frontend → Settings → Client Keys
Sentry.init({
  // ⚠️ PASTE CORRECT DSN HERE — Go to: sentry.io → aura-frontend → Settings → Client Keys (DSN)
  // Correct format: https://HASH@oNUMBER.ingest.us.sentry.io/NUMBER
  // Example:        https://abc123@o4512101.ingest.us.sentry.io/4512101212618752
  dsn: "https://5291a346035dced252023362ef2cc04f@o4512101179260928.ingest.us.sentry.io/4512101212618752",
  environment: "production",
  release: "aura-saas-frontend@1.0.0",
  integrations: [
    Sentry.browserTracingIntegration(),   // Tracks page load speed and API call timing
    Sentry.replayIntegration({
      maskAllText: true,        // Masks all text in session replays — no patient data recorded
      blockAllMedia: true,      // Blocks all images/media in replays
    }),
  ],
  tracesSampleRate: 0.2,        // Track 20% of page loads for performance (free tier safe)
  replaysSessionSampleRate: 0.0,   // Don't record normal sessions (save free quota)
  replaysOnErrorSampleRate: 1.0,   // Record full session replay ONLY when an error happens
})
// ────────────────────────────────────────────────────────────────────────────

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
