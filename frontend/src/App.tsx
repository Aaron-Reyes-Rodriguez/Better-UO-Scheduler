import { useState } from 'react'
import './App.css'
import { fetchHealth } from './api'


function App() {
  const [health, setHealth] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // const [classData, setClassData] = useState<unknown>(null)
  // const [classId, setClassId] = useState<string | null>(null)

  
  // async function getClassData(classId: string) {
  //   console.log(classId)
  //   const data = await getClass(classId)
  //   setClassData(JSON.stringify(data))
  //   console.log(classData)
  // }

  // const handleClassData = (event: React.ChangeEvent<HTMLInputElement>) => {
  //   // 2. Update the state with the current text box value
  //   setClassId(event.target.value);
  // };

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


    </>
  )
}
export default App
