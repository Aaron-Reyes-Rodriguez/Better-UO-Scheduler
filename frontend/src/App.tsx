import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import 

function App() {
  const [count, setCount] = useState(0)

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
        <button onClick={}>
          count is {count}
        </button>

      </div>
      <p className="read-the-docs">
        Click on the Vit and React logos to learn more
      </p>
    </>
  )
}

export default App
