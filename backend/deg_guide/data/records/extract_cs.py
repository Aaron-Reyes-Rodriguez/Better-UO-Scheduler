from pathlib import Path
import pandas as pd


GRADE_COLS = ["AP", "A", "AM", "BP", "B", "BM", "CP", "C", "CM", "DP", "D", "DM", "F"]


def weighted_gpa(df: pd.DataFrame) -> pd.Series:
    return (
        df["A_count"] * 4.0
        + df["B_count"] * 3.0
        + df["C_count"] * 2.0
        + df["D_count"] * 1.0
    ) / df["total_students"]


def main() -> None:
    base_dir = Path(__file__).parent
    xlsx_path = base_dir / "pub_rec_master_f2015-u2025.xlsx"

    out_course_prof = base_dir / "cs_course_professor.csv"
    out_courses = base_dir / "cs_courses.csv"
    out_professors = base_dir / "cs_professors.csv"

    if not xlsx_path.exists():
        raise FileNotFoundError(f"file not found: {xlsx_path}")

    # Load/normalzie headers
    df = pd.read_excel(xlsx_path)
    df.columns = df.columns.str.strip()

    term_descr_col = "TERM_DESC"
    instr_col = "INSTRUCTOR"

    # Validate cols
    required = {"TERM", term_descr_col, "SUBJ", "NUMB", "CRN", instr_col, *GRADE_COLS}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {sorted(missing)}")

    # Course filter
    df = df[df["SUBJ"].astype(str).str.strip().str.upper() == "CS"].copy()

    # Convert * and blanks to 0
    df[GRADE_COLS] = (
        df[GRADE_COLS]
        .replace("*", 0)
        .infer_objects(copy=False)
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
    )

    # Combine all letter grades
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

    df["course_number"] = df["NUMB"].astype(int)
    df["course_id"] = "CS " + df["course_number"].astype(str)
    df["term_code"] = df["TERM"].astype(str).str.strip()
    df["term"] = df[term_descr_col].astype(str).str.strip()
    df["professor"] = (
        df[instr_col]
        .astype(str)
        .str.replace("*", "", regex=False)
        .str.strip()
    )

    # 1) TERM + COURSE + PROF
    course_prof = (
        df.groupby(["term_code", "term", "course_id", "course_number", "professor"], as_index=False)[
            ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
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
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["term_code", "course_number", "professor"], ascending=[True, True, True])

    course_prof.to_csv(out_course_prof, index=False, encoding="utf-8")

    # 2) COURSE (ALL TERMS)
    courses = (
        course_prof.groupby(["course_id", "course_number"], as_index=False)[
            ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
        ]
        .sum()
    )
    courses["avg_gpa"] = weighted_gpa(courses).round(3)

    courses = courses[
        [
            "course_id",
            "course_number",
            "total_students",
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["course_number"], ascending=True)

    courses.to_csv(out_courses, index=False, encoding="utf-8")

    # 3) PROFESSOR (ALL TERMS)
    professors = (
        course_prof.groupby(["professor"], as_index=False)[
            ["A_count", "B_count", "C_count", "D_count", "F_count", "total_students"]
        ]
        .sum()
    )
    professors["avg_gpa"] = weighted_gpa(professors).round(3)

    # Add courses taught
    prof_courses = (
        course_prof.groupby("professor")["course_id"]
        .apply(lambda s: sorted(set(s.tolist())))
    )
    professors["courses_taught_count"] = professors["professor"].map(lambda p: len(prof_courses.get(p, [])))
    professors["courses_taught"] = professors["professor"].map(lambda p: "; ".join(prof_courses.get(p, [])))

    professors = professors[
        [
            "professor",
            "courses_taught_count",
            "courses_taught",
            "total_students",
            "A_count",
            "B_count",
            "C_count",
            "D_count",
            "F_count",
            "avg_gpa",
        ]
    ].sort_values(["professor"], ascending=True)

    professors.to_csv(out_professors, index=False, encoding="utf-8")

    print(f"Generated: {out_course_prof}")
    print(f"Generated: {out_courses}")
    print(f"Generated: {out_professors}")


if __name__ == "__main__":
    main()
