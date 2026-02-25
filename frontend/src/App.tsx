import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { fetchHealth, getClass } from './api'


function App() {
  const [health, setHealth] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [classData, setClassData] = useState<unknown>(null)
  const [classId, setClassId] = useState<string | null>(null)

  
  async function getClassData(classId: string) {
    console.log(classId)
    const data = await getClass(classId)
    setClassData(JSON.stringify(data))
    console.log(classData)
  }

  const handleClassData = (event: React.ChangeEvent<HTMLInputElement>) => {
    // 2. Update the state with the current text box value
    setClassId(event.target.value);
  };

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
      </div>

      <div className="card">
        <button onClick={checkBackend} disabled={loading}>
          Check API health
        </button>

        {loading && <p>Loading…</p>}
        {error && <p style={{ color: 'red' }}>{error}</p>}
        {health != null && <pre>{health}</pre>}
      </div>


      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
      
      <div className="card"></div>
        <input 
          type="text" 
          value={classId || ''} // Binds the box to the state
          onChange={handleClassData} // Fires on every keystroke
        />
        <button onClick={() => getClassData(classId || '')} disabled={loading || !classId}>
          Get Class Data
        </button>
    </>
  )
}
export default App
