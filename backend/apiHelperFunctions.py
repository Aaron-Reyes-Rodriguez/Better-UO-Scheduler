import json
import re
from functools import lru_cache
import psycopg2
from psycopg2.extras import RealDictCursor
import os

PROF_TAGS_FILE = "ClassProfessorData/jsonData/professor_tags.json"


def _normalize_class_key(class_id: str) -> str:
    return ''.join((class_id or '').upper().split())


def _compact(value: str) -> str:
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
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", (value or "").lower())
    raw_tokens = [tok for tok in cleaned.split() if tok]
    normalized = [NICKNAMES.get(tok, tok) for tok in raw_tokens]
    return tuple(normalized)


def _professor_aliases(key: str, display_name: str) -> set[str]:
    aliases: set[str] = set()
    aliases.add(_compact(key))
    aliases.add(_compact(display_name))

    if ',' in display_name:
        last, rest = [part.strip() for part in display_name.split(',', 1)]
        aliases.add(_compact(f"{rest} {last}"))

    return {a for a in aliases if a}


def _class_display_tokens(record: dict) -> tuple[str, ...]:
    return _name_tokens(record.get("course_id", ""))


def _prof_display_tokens(record: dict, key: str) -> tuple[str, ...]:
    return _name_tokens(record.get("professor_name", key))


@lru_cache(maxsize=1)
def _load_class_data() -> dict:
    with open("ClassProfessorData/jsonData/classes.json", "r") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_prof_data() -> dict:
    with open("ClassProfessorData/jsonData/professors.json", "r") as f:
        return json.load(f)



def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(db_url)

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS professor_tags (
                    id SERIAL PRIMARY KEY,
                    professor_id VARCHAR NOT NULL,
                    tag_name VARCHAR NOT NULL,
                    tag_count INTEGER DEFAULT 1,
                    UNIQUE(professor_id, tag_name)
                )
            """)
        conn.commit()
    finally:
        conn.close()

def _load_prof_tags(professor_id: str) -> list[str]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tag_name, tag_count
                FROM professor_tags 
                WHERE professor_id = %s AND tag_count > 1
                ORDER BY tag_count DESC
            """, (professor_id,))
            rows = cur.fetchall()
            # Return strings formatted like "Tag Name (3)" if we want to show counts
            # But the UI currently handles exact string matches to highlight buttons
            # Let's just return the raw strings so the UI selection works exactly as before.
            # Next iterations could expand the UI to accept counts.
            return [row[0] for row in rows]
    except Exception as e:
        print(f"Error loading tags for {professor_id}: {e}")
        return []
    finally:
        conn.close()

def classFinder(class_id):
    class_data = _load_class_data()

    key = class_id if class_id in class_data else _normalize_class_key(class_id)
    return class_data[key]


def professorFinder(professor_id):
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
    # Ensure professor exists, throws KeyError if not
    prof = professorFinder(professor_id)
    clean_prof_id = prof.get("professor", professor_id)
    
    unique_tags = list(dict.fromkeys(tags))
    if not unique_tags:
        return _load_prof_tags(clean_prof_id)
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for tag in unique_tags:
                cur.execute("""
                    INSERT INTO professor_tags (professor_id, tag_name, tag_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (professor_id, tag_name) 
                    DO UPDATE SET tag_count = professor_tags.tag_count + 1
                """, (clean_prof_id, tag))
        conn.commit()
    except Exception as e:
        print(f"Error updating tags for {clean_prof_id}: {e}")
        conn.rollback()
    finally:
        conn.close()
        
    return _load_prof_tags(clean_prof_id)

