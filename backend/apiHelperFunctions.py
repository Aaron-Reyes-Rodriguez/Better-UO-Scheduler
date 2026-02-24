import pandas as pd
import json
from pathlib import Path


def _normalize_class_key(class_id: str) -> str:
    return ''.join((class_id or '').upper().split())


def _compact_name(value: str) -> str:
    return ''.join(ch.lower() for ch in (value or '') if ch.isalnum())


def _name_tokens(value: str) -> tuple[str, ...]:
    cleaned = ''.join(ch if ch.isalnum() else ' ' for ch in (value or '').lower())
    return tuple(tok for tok in cleaned.split() if tok)


def _professor_aliases(key: str, display_name: str) -> set[str]:
    aliases: set[str] = set()
    aliases.add(_compact_name(key))
    aliases.add(_compact_name(display_name))

    if ',' in display_name:
        last, rest = [part.strip() for part in display_name.split(',', 1)]
        aliases.add(_compact_name(f"{rest} {last}"))

    return {a for a in aliases if a}


def classFinder(class_id):
    with open("ClassProfessorData/jsonData/classes.json", "r") as f:
        class_data = json.load(f)

    key = class_id if class_id in class_data else _normalize_class_key(class_id)
    return class_data[key]


def professorFinder(professor_id):
    with open("ClassProfessorData/jsonData/professors.json", "r") as f:
        professor_data = json.load(f)

    if professor_id in professor_data:
        return professor_data[professor_id]

    query_compact = _compact_name(professor_id)
    query_tokens = _name_tokens(professor_id)

    # First try compact aliases (supports "Last, First" and "First Last").
    for key, record in professor_data.items():
        display_name = record.get("professor_name", key)
        if query_compact in _professor_aliases(key, display_name):
            return record

    # Fallback 1: exact token-set match for flexible spacing/punctuation and middle names.
    query_token_set = set(query_tokens)
    for key, record in professor_data.items():
        display_name = record.get("professor_name", key)
        if set(_name_tokens(display_name)) == query_token_set:
            return record

    # Fallback 2: allow subset matching (e.g., "Michael Hennessy" matches
    # "Hennessy, Michael Shane") when it is a unique/best match.
    subset_matches = []
    for key, record in professor_data.items():
        display_name = record.get("professor_name", key)
        display_tokens = set(_name_tokens(display_name))
        if query_token_set and query_token_set.issubset(display_tokens):
            extra_tokens = len(display_tokens - query_token_set)
            subset_matches.append((extra_tokens, len(display_tokens), display_name, record))

    if subset_matches:
        subset_matches.sort(key=lambda x: (x[0], x[1], x[2]))
        return subset_matches[0][3]

    raise KeyError(professor_id)


# Global variable to store transcript data in memory
transcriptData = {}


def saveTranscriptData(data):
    """
    Save the parsed transcript data to the global variable
    """
    global transcriptData
    transcriptData = data


def getTranscriptData():
    """
    Parse the backend transcript and send it back to the frontend
    """
    global transcriptData
    return transcriptData
