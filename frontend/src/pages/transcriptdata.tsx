import { useLocation } from "react-router-dom"

type TranscriptData = {
  broad_data: {
    student_name: string | null
    gpa: number | null
    earned_credits: number | null
    program: string | null
    level: string | null
    catalog_year: string | null
    declared_major: { name: string; catalog_year: string } | null
    /** Present when transcript has multiple majors (double major); first major also in declared_major */
    declared_majors?: { name: string; catalog_year: string }[]
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

export default function TranscriptDataView() {
  const location = useLocation()
  let data = location.state?.transcriptData as TranscriptData | undefined

  if (!data) {
    const storedData = localStorage.getItem("transcriptData") || localStorage.getItem("auditData");
    if (storedData) {
      try {
        data = JSON.parse(storedData);
      } catch (e) {
        console.error("Failed to parse transcriptData from localStorage", e);
      }
    }
  }

  if (!data) return <p style={{ color: "red" }}>Error: No transcript data found. Please upload a transcript first.</p>

  return <pre>{JSON.stringify(data, null, 2)}</pre>
}