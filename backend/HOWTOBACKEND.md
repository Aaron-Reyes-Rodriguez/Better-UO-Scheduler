# Better-UO-Scheduler — Data & Update Guide

This document explains **how to add or modify data** in the project without touching solver logic.

The system is **data-driven**:
- Courses live in one catalog file
- Degree types (BA / BS) live in their own files
- Majors and minors each have their own files
- The solver reads these files and figures everything out automatically

You should **never need to edit solver code** to add a new major.

---

## High-level philosophy (IMPORTANT)

**Course Catalog**
- Stores *facts* about courses
- Only includes **university-wide / general-degree tags**
- Does **NOT** include major-specific classifications

**Programs (Degree Types / Majors / Minors)**
- Define their own course groupings using `sets`
- Define rules using `requirements`
- Reference courses by ID (`"CS210"`, `"MATH251"`, etc.)

This design scales to many majors without exploding the number of tags.

---

# 1) Editing the Course Catalog

**File:** `deg_guide/data/catalog_courses.json`

### What belongs here
Each course should appear **once**, with factual information.

### Required fields (per course)
- **id** — canonical course code **without spaces** (example: `"CS210"`, not `"CS 210"`)
- **subject** — department code (example: `"CS"`, `"MATH"`)
- **number** — course number (integer, example: `210`)
- **credits** — integer
- **level** — usually `100` / `200` / `300` / `400`
- **tags** — list (often empty)

Example entry:

```json
{
  "id": "CS210",
  "subject": "CS",
  "number": 210,
  "credits": 4,
  "level": 200,
  "tags": []
}
```

### What tags are allowed here
Only **university-wide / general-degree tags**, such as:
- **Areas of Inquiry (AoI):**
  - `aoi_arts_letters`
  - `aoi_social_science`
  - `aoi_science`
- **Writing requirements**
- **Other global graduation categories**

If you’re not sure whether a tag is global, **don’t add it**—leave `tags: []`.

### What should NOT go here
Do **NOT** add major/minor-specific tags like:
- `core_major_cs`
- `upper_div_cs`
- `capstone_option`
- `math_major_core`

Those belong in the **major/minor program files**, not the catalog.

### Adding a new course
1. Add a new object to `catalog_courses.json`
2. Make sure the **id** matches what transcripts and program files will use
3. Only add **global** tags if truly applicable

---

# 2) Editing Degree Type Files (BA / BS)

**Folder:** `deg_guide/data/programs/uo_degree_types/`

Degree types define **top-level graduation rules** that apply to many majors (ex: BA language requirement, BS math/science requirement).

### Example: Bachelor of Science (BS)

```json
{
  "id": "UO_BS",
  "name": "UO Bachelor of Science",
  "sets": {
    "bs_math_cis_year": ["MATH251", "MATH252", "CIS210"]
  },
  "requirements": [
    {
      "id": "bs_math_requirement",
      "type": "credits_at_least",
      "min_credits": 12,
      "from_set": "bs_math_cis_year"
    }
  ],
  "overlap_rules": []
}
```

### Important change (new system)
Do **not** rely on course tags like `bs_math_cis`.

Instead, use either:
- `from_set` (explicit list), or
- `where` filters (subject/level rules)

Example using `where`:

```json
{
  "type": "credits_at_least",
  "min_credits": 12,
  "where": { "subject": "MATH", "min_number": 200 }
}
```

### Does BS need updating?
✅ **Yes, if it currently relies on tags like `bs_math_cis`.**  
Convert it to use **sets** or **where** filters.

---

# 3) Editing Major / Minor Files

**Folders:**
- `deg_guide/data/programs/majors/`
- `deg_guide/data/programs/minors/`

Each major or minor has **one JSON file**.

### Major / Minor structure

```json
{
  "id": "MAJOR_CS",
  "name": "Computer Science Major",
  "sets": {
    "cs_core": ["CS210", "CS211", "CS212"],
    "cs_capstone": ["CS422", "CS431"],
    "cs_theory": ["CS315", "CS330"]
  },
  "requirements": [
    { "id": "core", "type": "all_of", "from_set": "cs_core" },
    { "id": "theory", "type": "choose_k", "k": 1, "from_set": "cs_theory" },
    {
      "id": "upper_div",
      "type": "credits_at_least",
      "min_credits": 12,
      "where": { "subject": "CS", "min_number": 300 }
    }
  ],
  "overlap_rules": [
    { "type": "no_double_counting_default" }
  ]
}
```

### What are `sets`?
`sets` are **program-local course lists** (local to that major/minor/degree type), used for:
- Core requirements
- Elective pools
- Capstone options

They prevent the course catalog from needing major-specific tags.

A course can appear in:
- multiple sets
- multiple majors  
…without changing the catalog.

### Requirement types (MVP)
- **all_of** — all courses in a set are required
- **choose_k** — choose K courses from a set
- **credits_at_least** — minimum credits from a set or from a `where` filter

### Adding a new major/minor
1. Create a new JSON file in `majors/` or `minors/`
2. Define `sets` for any special course pools
3. Add `requirements` using:
   - `from_set` for explicit lists
   - `where` for subject/level rules
4. No solver changes required

---

# 4) Testing the System (Audit Endpoint)

### Start the backend
From the `backend/` directory:

```bash
uvicorn app:app --reload
```

### Open the API docs
Go to:

- `http://127.0.0.1:8000/docs`

### Example request

```json
{
  "taken_courses": ["CS210", "CS211", "CS315"]
}
```

This represents a parsed transcript:
- Course IDs must match `catalog_courses.json`
- Order does not matter

### Expected response
The response will include:
- overall completion percentage
- which courses counted toward which requirements
- what requirements are still missing (slack)
