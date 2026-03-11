"""
File: apiHelperFunctions.py
Purpose: Data-access and business-logic helpers for the Better-UO-Scheduler
         backend (Quackademics). Provides functions for looking up class and
         professor records from static JSON files, generating typeahead
         suggestions, and managing professor tags stored in PostgreSQL.
Created: 2024
Authors: Aaron Reyes-Rodriguez and contributors

System: Better-UO-Scheduler (Quackademics)
  This module is imported by app.py (the FastAPI server). It is responsible for
  all database interactions with the professor_tags table and all in-memory
  lookups against the pre-built classes.json and professors.json files.
"""

# json: standard library module for reading/writing JSON data files.
import json
# re: standard library regex module used for fuzzy name matching.
import re
# lru_cache: memoisation decorator that ensures the large JSON files are loaded
# from disk only once and cached for the lifetime of the process.
from functools import lru_cache
# psycopg2: PostgreSQL adapter used to store and retrieve professor tag votes.
import psycopg2
# RealDictCursor: cursor factory that returns rows as dicts keyed by column name.
from psycopg2.extras import RealDictCursor
import os

PROF_TAGS_FILE = "ClassProfessorData/jsonData/professor_tags.json"

# Mapping from display tag name -> database column name
TAG_COLUMNS = {
    "Tough Grader": "tough_grader",
    "Get Ready To Read": "get_ready_to_read",
    "Participation Matters": "participation_matters",
    "Skip Class? You Won't Pass.": "skip_class_you_wont_pass",
    "Accessible Outside Class": "accessible_outside_class",
    "Caring": "caring",
    "Respected": "respected",
    "Lecture Heavy": "lecture_heavy",
    "Test Heavy": "test_heavy",
    "Graded by few things": "graded_by_few_things",
    "Amazing lectures": "amazing_lectures",
    "Clear grading criteria": "clear_grading_criteria",
    "Hilarious": "hilarious",
    "Inspirational": "inspirational",
    "Lots of homework": "lots_of_homework",
}

# Reverse mapping: column name -> display tag name
COLUMN_TO_TAG = {v: k for k, v in TAG_COLUMNS.items()}


def _normalize_class_key(class_id: str) -> str:
    """
    Normalise a raw class identifier to the form used as a JSON key.
    Strips whitespace and uppercases (e.g. "cs 210" -> "CS210").

    Args:
        class_id (str): Raw course identifier string.

    Returns:
        str: Normalised class key with no spaces and all uppercase.
    """
    return ''.join((class_id or '').upper().split())


def _compact(value: str) -> str:
    """
    Produce a compact lowercase alphanumeric representation of a string by
    removing all non-alphanumeric characters. Used for fuzzy alias matching.

    Args:
        value (str): Any string (e.g. a professor name).

    Returns:
        str: Lowercase string with only alphanumeric characters.
    """
    return ''.join(ch.lower() for ch in (value or '') if ch.isalnum())


NICKNAMES = {
    "phil": "phillip",
    "philip": "phillip",
    "mike": "michael",
    "dave": "david",
    "will": "william",
    "bill": "william",
    "bob": "robert",
    "rob": "robert",
    "tom": "thomas",
    "jim": "james",
}


def _name_tokens(value: str) -> tuple[str, ...]:
    """
    Tokenise a string for name-matching purposes, replacing common nicknames
    with their canonical forms (e.g. "Mike" -> "michael").

    Args:
        value (str): A name or display string.

    Returns:
        tuple[str, ...]: Tuple of lowercase normalised tokens.
    """
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", (value or "").lower())
    raw_tokens = [tok for tok in cleaned.split() if tok]
    normalized = [NICKNAMES.get(tok, tok) for tok in raw_tokens]
    return tuple(normalized)


def _professor_aliases(key: str, display_name: str) -> set[str]:
    """
    Build a set of compact alias strings for a professor to support searches in
    multiple name formats ("Last, First", "First Last", raw key).

    Args:
        key (str): The raw professor key from the JSON data.
        display_name (str): The human-readable professor name.

    Returns:
        set[str]: Set of compact lowercase alphanumeric alias strings.
    """
    aliases: set[str] = set()
    aliases.add(_compact(key))
    aliases.add(_compact(display_name))

    if ',' in display_name:
        last, rest = [part.strip() for part in display_name.split(',', 1)]
        aliases.add(_compact(f"{rest} {last}"))

    return {a for a in aliases if a}


def _class_display_tokens(record: dict) -> tuple[str, ...]:
    """
    Extract display tokens for a class record used in suggestion scoring.

    Args:
        record (dict): A single class record from classes.json.

    Returns:
        tuple[str, ...]: Normalised name tokens derived from the course_id field.
    """
    return _name_tokens(record.get("course_id", ""))


def _prof_display_tokens(record: dict, key: str) -> tuple[str, ...]:
    """
    Extract display tokens for a professor record used in suggestion scoring.

    Args:
        record (dict): A single professor record from professors.json.
        key (str): The raw professor key (fallback if professor_name is absent).

    Returns:
        tuple[str, ...]: Normalised name tokens derived from the professor's name.
    """
    return _name_tokens(record.get("professor_name", key))


@lru_cache(maxsize=1)
def _load_class_data() -> dict:
    """
    Load the classes.json file into memory. The result is cached (maxsize=1) so
    the file is only read from disk on the first call.

    Returns:
        dict: Mapping of course-ID strings to class data records.
    """
    with open("ClassProfessorData/jsonData/classes.json", "r") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_prof_data() -> dict:
    """
    Load the professors.json file into memory. The result is cached (maxsize=1)
    so the file is only read from disk on the first call.

    Returns:
        dict: Mapping of professor-ID strings to professor data records.
    """
    with open("ClassProfessorData/jsonData/professors.json", "r") as f:
        return json.load(f)



def get_db_connection():
    """
    Create and return a new psycopg2 database connection using the DATABASE_URL
    environment variable.

    Returns:
        psycopg2.connection: An open PostgreSQL connection object.

    Raises:
        ValueError: If the DATABASE_URL environment variable is not set.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(db_url)

def init_db():
    """Create the professor_tags table with one column per tag."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Build column definitions for each tag
            tag_col_defs = ",\n                    ".join(
                f"{col} INTEGER DEFAULT 0" for col in TAG_COLUMNS.values()
            )
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS professor_tags (
                    id SERIAL PRIMARY KEY,
                    professor_id VARCHAR NOT NULL UNIQUE,
                    {tag_col_defs}
                )
            """)
        conn.commit()
    finally:
        conn.close()

def _load_prof_tags(professor_id: str) -> list[dict]:
    """Load tags for a professor from the pivot table. Returns tags with count >= 1 as dicts."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            tag_cols = ", ".join(TAG_COLUMNS.values())
            cur.execute(f"""
                SELECT {tag_cols}
                FROM professor_tags 
                WHERE professor_id = %s
            """, (professor_id,))
            row = cur.fetchone()
            if not row:
                return []
            # Return tag dicts with name and count where count >= 1
            col_names = list(TAG_COLUMNS.values())
            tags = []
            for i, count in enumerate(row):
                if count and count >= 1:
                    tags.append({"name": COLUMN_TO_TAG[col_names[i]], "count": count})
            # Sort by count descending
            tags.sort(key=lambda x: -x["count"])
            return tags
    except Exception as e:
        print(f"Error loading tags for {professor_id}: {e}")
        return []
    finally:
        conn.close()

def classFinder(class_id):
    """
    Look up a class record by its identifier, with normalisation fallback
    (e.g. "cs 210" or "CS 210" will both find "CS210").

    Args:
        class_id (str): Raw course identifier supplied by the caller.

    Returns:
        dict: The class record from classes.json.

    Raises:
        KeyError: If no matching class is found.
    """
    class_data = _load_class_data()

    key = class_id if class_id in class_data else _normalize_class_key(class_id)
    return class_data[key]


def professorFinder(professor_id):
    """
    Look up a professor record with progressively more lenient matching:
      1. Exact key match.
      2. Compact alias match (handles "Last, First" and "First Last").
      3. Exact token-set match (ignores ordering).
      4. Subset + prefix scoring (handles partial names like "Phil Colbert").

    After finding the record the function attaches the professor's current tag
    votes from the PostgreSQL database.

    Args:
        professor_id (str): Raw professor name or identifier to search for.

    Returns:
        dict: Professor record from professors.json enriched with a "tags" list.

    Raises:
        KeyError: If no matching professor is found.
    """
    professor_data = _load_prof_data()

    found_record = None
    found_key = None

    if professor_id in professor_data:
        found_record = professor_data[professor_id]
        found_key = professor_id
    else:
        query_compact = _compact(professor_id)
        query_tokens = _name_tokens(professor_id)
        if not query_tokens:
            raise KeyError(professor_id)
        query_token_set = set(query_tokens)

        # First try compact aliases (supports "Last, First" and "First Last").
        for key, record in professor_data.items():
            display_name = record.get("professor_name", key)
            if query_compact in _professor_aliases(key, display_name):
                found_record = record
                found_key = key
                break
        
        if found_record is None:
            # Fallback 1: exact token-set match.
            for key, record in professor_data.items():
                if set(_prof_display_tokens(record, key)) == query_token_set:
                    found_record = record
                    found_key = key
                    break

        if found_record is None:
            # Fallback 2: subset + prefix scoring for shorter inputs (e.g., "Phil Colbert").
            subset_matches = []
            for key, record in professor_data.items():
                tokens = _prof_display_tokens(record, key)
                display_tokens = set(tokens)
                if query_token_set and query_token_set.issubset(display_tokens):
                    extra_tokens = len(display_tokens - query_token_set)
                    prefix_bonus = sum(
                        any(display_tok.startswith(q) for display_tok in tokens)
                        for q in query_tokens
                    )
                    subset_matches.append((extra_tokens, -prefix_bonus, len(display_tokens), record.get("professor_name", key), record, key))

            if subset_matches:
                subset_matches.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
                found_record = subset_matches[0][4]
                found_key = subset_matches[0][5]

    if found_record is None:
        raise KeyError(professor_id)
        
    result = dict(found_record)
    result["professor"] = found_key
    result["tags"] = _load_prof_tags(found_key)
    return result


def classSuggestions(query: str, limit: int = 8) -> list[str]:
    """
    Return a ranked list of class name suggestions matching a partial query.
    Scoring favours prefix matches, then substring matches, then token overlap.

    Args:
        query (str): Partial course name or ID typed by the user.
        limit (int): Maximum number of results to return (capped at 20).

    Returns:
        list[str]: Ordered list of matching course display names.
    """
    q = (query or "").strip()
    if len(q) < 1:
        return []

    compact = _compact(q)
    q_tokens = _name_tokens(q)
    out = []
    class_data = _load_class_data()

    for key, record in class_data.items():
        display = record.get("course_id", key)
        display_compact = _compact(display)
        tokens = _class_display_tokens(record)
        token_set = set(tokens)
        q_set = set(q_tokens)

        score = 0
        if display_compact.startswith(compact):
            score += 100
        elif compact in display_compact:
            score += 65
        if q_set and q_set.issubset(token_set):
            score += 40
        score += sum(any(tok.startswith(qt) for tok in tokens) for qt in q_tokens) * 8
        if score > 0:
            out.append((score, display))

    out.sort(key=lambda x: (-x[0], x[1]))
    return [name for _, name in out[:max(1, min(limit, 20))]]


def professorSuggestions(query: str, limit: int = 8) -> list[str]:
    """
    Return a ranked list of professor name suggestions matching a partial query.
    Scoring favours alias prefix matches, then alias substring matches, then
    token overlap.

    Args:
        query (str): Partial professor name typed by the user.
        limit (int): Maximum number of results to return (capped at 20).

    Returns:
        list[str]: Ordered list of matching professor display names.
    """
    q = (query or "").strip()
    if len(q) < 1:
        return []

    compact = _compact(q)
    q_tokens = _name_tokens(q)
    q_set = set(q_tokens)
    out = []
    professor_data = _load_prof_data()

    for key, record in professor_data.items():
        display = record.get("professor_name", key)
        aliases = _professor_aliases(key, display)
        tokens = _prof_display_tokens(record, key)
        token_set = set(tokens)

        score = 0
        if any(alias.startswith(compact) for alias in aliases):
            score += 110
        elif any(compact in alias for alias in aliases):
            score += 75
        if q_set and q_set.issubset(token_set):
            score += 45
        score += sum(any(tok.startswith(qt) for tok in tokens) for qt in q_tokens) * 9
        if score > 0:
            out.append((score, display))

    out.sort(key=lambda x: (-x[0], x[1]))
    return [name for _, name in out[:max(1, min(limit, 20))]]


def updateProfessorTags(professor_id: str, tags: list[str]) -> list[str]:
    """
    Increment the vote count for each specified tag for a professor in the
    professor_tags PostgreSQL table. On first vote an INSERT is performed;
    subsequent votes use ON CONFLICT … DO UPDATE to increment the column.

    Args:
        professor_id (str): Raw professor identifier (will be resolved and
            normalised via professorFinder before database write).
        tags (list[str]): List of tag display-names to vote for. Duplicate
            and unrecognised tags are silently ignored.

    Returns:
        list[str]: Updated list of TagWithCount dicts for this professor from
            the database after the write, filtered to tags with count >= 1.

    Raises:
        KeyError: If the professor cannot be found.
    """
    # Ensure professor exists, throws KeyError if not
    prof = professorFinder(professor_id)
    clean_prof_id = prof.get("professor", professor_id)
    
    unique_tags = list(dict.fromkeys(tags))
    if not unique_tags:
        return _load_prof_tags(clean_prof_id)
    
    # Filter to only valid tags that have column mappings
    valid_tags = [t for t in unique_tags if t in TAG_COLUMNS]
    if not valid_tags:
        return _load_prof_tags(clean_prof_id)
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Build the INSERT with ON CONFLICT to increment tag columns
            tag_col_names = [TAG_COLUMNS[t] for t in valid_tags]
            
            # Insert a new row with count=1 for selected tags, or increment on conflict
            all_cols = list(TAG_COLUMNS.values())
            insert_values = []
            for col in all_cols:
                if col in tag_col_names:
                    insert_values.append("1")
                else:
                    insert_values.append("0")
            
            update_parts = [f"{col} = professor_tags.{col} + 1" for col in tag_col_names]
            
            cur.execute(f"""
                INSERT INTO professor_tags (professor_id, {", ".join(all_cols)})
                VALUES (%s, {", ".join(insert_values)})
                ON CONFLICT (professor_id) 
                DO UPDATE SET {", ".join(update_parts)}
            """, (clean_prof_id,))
        conn.commit()
    except Exception as e:
        print(f"Error updating tags for {clean_prof_id}: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    return _load_prof_tags(clean_prof_id)

