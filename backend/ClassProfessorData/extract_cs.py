"""
File: extract_cs.py
Purpose: Data-processing script for the Better-UO-Scheduler (Quackademics)
         project. Reads raw grade-distribution data from the UO public records
         Excel file and produces four aggregated CSV files used by the backend
         API: per-term course+professor data, all-time course data, all-time
         professor data, and course+professor (all-time) data.
Created: 2024
Authors: Aaron Reyes-Rodriguez and contributors

System: Better-UO-Scheduler (Quackademics)
  Run this script once (or whenever the source data is updated) to regenerate
  the CSV files in ClassProfessorData/. Those CSVs are then processed by
  data_sorter.py to build the JSON files consumed by the backend API.
"""

# pathlib.Path: used for portable file-path construction.
from pathlib import Path
# pandas: data-analysis library used for all CSV aggregation and groupby
# operations throughout this script.
import pandas as pd


GRADE_COLS = ["AP", "A", "AM", "BP", "B", "BM", "CP", "C", "CM", "DP", "D", "DM", "F"]

# Wsubjucts
SUBJECTS = {"CS", "CIS"}


def weighted_gpa(df: pd.DataFrame) -> pd.Series:
    """
    Calculate the weighted average GPA for each row in a DataFrame using the
    standard 4.0 scale grade distribution columns.

    Args:
        df (pd.DataFrame): DataFrame containing grade-count columns (AP, A, AM,
            BP, B, BM, CP, C, CM, DP, D, DM, F) and a total_students column.

    Returns:
        pd.Series: Weighted GPA values (one per row), not yet rounded.
    """
    return (
        df["AP"] * 4.0
        + df["A"] * 4.0
        + df["AM"] * 3.7
        + df["BP"] * 3.3
        + df["B"] * 3.0
        + df["BM"] * 2.7
        + df["CP"] * 2.3
        + df["C"] * 2.0
        + df["CM"] * 1.7
        + df["DP"] * 1.3
        + df["D"] * 1.0
        + df["DM"] * 0.7
    ) / df["total_students"]

def get_course_professor_term_data(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Aggregate grade data by term, course, and professor and write the result to
    a CSV file. This is the primary aggregation used as input for all other
    aggregation functions.

    Args:
        df (pd.DataFrame): Cleaned source DataFrame from clean_up_data.
        output_path (Path): Destination path for the output CSV file.

    Returns:
        pd.DataFrame: Aggregated DataFrame sorted by term_code, course_id,
            and professor.
    """
    # 1) TERM + COURSE + PROF
    course_prof = (
        df.groupby(["term_code", "term", "course_id", "course_number", "professor"], as_index=False)[
            GRADE_COLS + ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
        ]
        .sum()
    )
    course_prof["avg_gpa"] = weighted_gpa(course_prof).round(3)

    course_prof = course_prof[
        [
            "term_code",
            "term",
            "course_id",
            "course_number",
            "professor",
            "total_students",
            *GRADE_COLS,
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["term_code", "course_id", "professor"], ascending=[True, True, True])

    course_prof.to_csv(output_path, index=False, encoding="utf-8")
    return course_prof

def get_class_data(course_prof: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Aggregate grade data across all terms for each unique course and write the
    result to a CSV file.

    Args:
        course_prof (pd.DataFrame): Output DataFrame from
            get_course_professor_term_data.
        output_path (Path): Destination path for the output CSV file.

    Returns:
        pd.DataFrame: Course-level aggregated DataFrame sorted by course_id.
    """
    # 2) COURSE (ALL TERMS)
    courses = (
        course_prof.groupby(["course_id", "course_number"], as_index=False)[
            GRADE_COLS + ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
        ]
        .sum()
    )
    courses["avg_gpa"] = weighted_gpa(courses).round(3)

    courses = courses[
        [
            "course_id",
            "course_number",
            "total_students",
            *GRADE_COLS,
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["course_id"], ascending=True)

    courses.to_csv(output_path, index=False, encoding="utf-8")
    return courses

def get_professor_data(course_prof: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Aggregate grade data across all terms for each professor, append a list of
    courses they have taught, and write the result to a CSV file.

    Args:
        course_prof (pd.DataFrame): Output DataFrame from
            get_course_professor_term_data.
        output_path (Path): Destination path for the output CSV file.

    Returns:
        pd.DataFrame: Professor-level aggregated DataFrame sorted by professor
            name, including courses_taught and courses_taught_count columns.
    """
    # 3) PROFESSOR (ALL TERMS)
    professors = (
        course_prof.groupby(["professor"], as_index=False)[
            GRADE_COLS + ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
        ]
        .sum()
    )
    professors["avg_gpa"] = weighted_gpa(professors).round(3)

    # Add courses taught
    prof_courses = (
        course_prof.groupby("professor")["course_id"]
        .apply(lambda s: sorted(set(s.tolist())))
    )
    professors["courses_taught_count"] = professors["professor"].map(
        lambda p: len(prof_courses.get(p, []))
    )
    professors["courses_taught"] = professors["professor"].map(
        lambda p: "; ".join(prof_courses.get(p, []))
    )

    professors = professors[
        [
            "professor",
            "courses_taught_count",
            "courses_taught",
            "total_students",
            *GRADE_COLS,
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["professor"], ascending=True)

    professors.to_csv(output_path, index=False, encoding="utf-8")
    return professors

def get_class_professor_data(course_prof: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    Aggregate grade data across all terms for each unique course+professor
    pairing and write the result to a CSV file.

    Args:
        course_prof (pd.DataFrame): Output DataFrame from
            get_course_professor_term_data.
        output_path (Path): Destination path for the output CSV file.

    Returns:
        pd.DataFrame: Course+professor aggregated DataFrame sorted by course_id
            and professor.
    """
    # 4) CLASS + PROFESSOR (ALL TERMS)
    class_prof = (
        course_prof.groupby(["course_id", "course_number", "professor"], as_index=False)[
            GRADE_COLS + ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
        ]
        .sum()
    )
    class_prof["avg_gpa"] = weighted_gpa(class_prof).round(3)

    class_prof = class_prof[
        [
            "course_id",
            "course_number",
            "professor",
            "total_students",
            *GRADE_COLS,
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["course_id", "professor"], ascending=True)

    class_prof.to_csv(output_path, index=False, encoding="utf-8")
    return class_prof


def clean_up_data(file_path: Path) -> pd.DataFrame:
    """
    Load and clean the raw UO public-records Excel file. Normalises column
    names, filters to relevant subjects, maps CIS -> CS, converts grade columns
    to integers, computes aggregate letter-grade buckets and total_students, and
    drops rows with no recorded letter grade.

    Args:
        file_path (Path): Path to the raw Excel (.xlsx) grade-distribution file.

    Returns:
        pd.DataFrame: Cleaned DataFrame ready for aggregation, with columns:
            course_number, course_id, term_code, term, professor, and all
            GRADE_COLS plus A_count/B_count/C_count/D_count/F_count/total_students.

    Raises:
        FileNotFoundError: If the Excel file does not exist at file_path.
        KeyError: If required columns are missing from the Excel file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"file not found: {file_path}")

    # Load/normalize headers
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    term_descr_col = "TERM_DESC"
    instr_col = "INSTRUCTOR"

    # Validate cols
    required = {"TERM", term_descr_col, "SUBJ", "NUMB", "CRN", instr_col, *GRADE_COLS}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    # Filter CS + CIS
    df["SUBJ"] = df["SUBJ"].astype(str).str.strip().str.upper()
    #df = df[df["SUBJ"].isin(SUBJECTS)].copy()
    
    # Map CIS to CS to combine averages
    df["SUBJ"] = df["SUBJ"].replace("CIS", "CS")

    # Convert * and blanks to 0
    df[GRADE_COLS] = (
        df[GRADE_COLS]
        .replace("*", 0)
        .infer_objects(copy=False)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )

    # combined buckets (easy to work with)
    df["A_count"] = df["AP"] + df["A"] + df["AM"]
    df["B_count"] = df["BP"] + df["B"] + df["BM"]
    df["C_count"] = df["CP"] + df["C"] + df["CM"]
    df["D_count"] = df["DP"] + df["D"] + df["DM"]
    df["F_count"] = df["F"]

    df["total_students"] = (
        df["A_count"] + df["B_count"] + df["C_count"] + df["D_count"] + df["F_count"]
    )

    # Drop rows with no letter grade
    df = df[df["total_students"] > 0].copy()

    # IDs + cleanup
    df["course_number"] = df["NUMB"].astype(str).str.strip()
    df["course_id"] = df["SUBJ"] + " " + df["course_number"]
    df["term_code"] = df["TERM"].astype(str).str.strip()
    df["term"] = df[term_descr_col].astype(str).str.strip()
    df["professor"] = (
        df[instr_col]
        .astype(str)
        .str.replace("*", "", regex=False)
        .str.strip()
    )
    return df


def main() -> None:
    """
    CLI entry point. Reads the source Excel file and generates all four
    aggregated CSV output files in the ClassProfessorData directory.

    Returns:
        None
    """
    base_dir = Path(__file__).parent
    xlsx_path = base_dir / "../deg_guide/data/records/pub_rec_master_f2015-u2025.xlsx" 
    df = clean_up_data(xlsx_path)

    out_course_prof_term = base_dir / "course_professor_term.csv"
    out_courses = base_dir / "courses.csv"
    out_professors = base_dir / "professors.csv"
    out_course_prof = base_dir / "course_professor.csv"

    # 1) COURSE + Professor (PER TERM)
    course_prof_term = get_course_professor_term_data(df, out_course_prof_term)
    print(f"Generated: {out_course_prof_term}")
    # 2) COURSE (ALL TERMS)
    courses = get_class_data(course_prof_term, out_courses)
    print(f"Generated: {out_courses}")
    # 3) PROFESSOR (ALL TERMS)
    professors = get_professor_data(course_prof_term, out_professors)
    print(f"Generated: {out_professors}")
    # 4) CLASS + PROFESSOR (ALL TERMS)
    course_prof = get_class_professor_data(course_prof_term, out_course_prof)
    print(f"Generated: {out_course_prof}")


if __name__ == "__main__":
    main()

"BLAH BLAH BLAH BLAH BLAH BLAH"
