import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import Layout from './Layout.tsx'
import GeneralClass from './pages/general_class.tsx'
import GeneralProfessor from './pages/general_professor.tsx'
import Scheduler from './pages/scheduler.tsx'
import Search from './pages/search.tsx'
import TranscriptData from './pages/transcriptdata.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<App />} />
          <Route path="class" element={<GeneralClass />} />
          <Route path="professor" element={<GeneralProfessor />} />
          <Route path="scheduler" element={<Scheduler />} />
          <Route path="search" element={<Search />} />
          <Route path="transcriptdata" element={<TranscriptData />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)