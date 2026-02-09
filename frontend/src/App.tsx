import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { apiBase, auditCs, fetchHealth } from './api'

function App() {
  const [count, setCount] = useState(0)
  const [health, setHealth] = useState<string | null>(null)
  const [audit, setAudit] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function checkBackend() {
    setError(null)
    setHealth(null)
    setLoading(true)
    try {
      const data = await fetchHealth()
      setHealth(JSON.stringify(data))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  async function runAudit() {
    setError(null)
    setAudit(null)
    setLoading(true)
    try {
      // Example: empty transcript; replace with real attempts from your UI
      const result = await auditCs([])
      setAudit(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Audit failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Quackademics</h1>
      <div className="card">
        <button onClick={() => setCount((c) => c + 1)}>
          count is {count}
        </button>
      </div>

      <div className="card">
        <p>Backend: <code>{apiBase}</code></p>
        <p className="hint">Set VITE_API_URL in Amplify env, then redeploy so the build picks it up.</p>
        <button onClick={checkBackend} disabled={loading}>
          Check API health
        </button>
        <button onClick={runAudit} disabled={loading}>
          Run CS audit (empty)
        </button>
        {loading && <p>Loading…</p>}
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {health != null && <pre>{health}</pre>}
        {audit != null && <pre>{JSON.stringify(audit, null, 2)}</pre>}
      </div>

      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
    </>
  )
}

export default App
