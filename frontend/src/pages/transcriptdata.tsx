import { useEffect, useState } from "react"
import { getTranscriptData } from "../api"

type TranscriptData = {
  broad_data: {
    student_name: string | null
    gpa: number | null
    earned_credits: number | null
    program: string | null
    level: string | null
    catalog_year: string | null
    declared_major: { name: string; catalog_year: string } | null
    minors: { name: string; catalog_year: string }[]
  }
  taken_attempts: {
    attempt_id: string
    course_id: string
    credits_taken: number
    grading_basis: string
  }[]
  class_grades: Record<string, {
    course_id: string
    grade: string
    status: string
  }>
}

export default function TranscriptData() {
  const [data, setData] = useState<TranscriptData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getTranscriptData()
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <p style={{ color: "red" }}>Error: {error}</p>
  if (!data) return <p>Loading...</p>

  return <pre>{JSON.stringify(data, null, 2)}</pre>
}