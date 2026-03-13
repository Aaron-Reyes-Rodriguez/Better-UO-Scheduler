#!/usr/bin/env python3
"""
File: parse_catalog.py
Purpose: Parse course catalog PDF text and generate JSON catalog files,
         providing the standalone templates for specific course generation runs.
Authors: Daniel Asiamah

System: Better-UO-Scheduler (Quackademics)
"""
import json
import re
from pathlib import Path

def parse_credits(credits_str):
    """
    Parse a credit string denoting credit counts.
    
    Args:
        credits_str (str): Raw credits string (e.g., '4 Credits', '1-5 Credits').
        
    Returns:
        tuple[int, dict | None]: A default credit integer and a dictionary containing
        the credit range min/max bounds (or None if a fixed credit count).
    """
    credits_str = credits_str.strip()
    
    # Variable credits: "1-5 Credits"
    match = re.match(r'(\d+)-(\d+)', credits_str)
    if match:
        min_c, max_c = int(match.group(1)), int(match.group(2))
        default = 4 if max_c >= 4 else max_c
        return default, {"min": min_c, "max": max_c, "default": default}
    
    # Single credit: "4 Credits"
    match = re.match(r'(\d+)', credits_str)
    if match:
        return int(match.group(1)), None
    
    return 4, None

def extract_prereqs(text):
    """
    Extract prerequisite course IDs from a block of text.
    
    Args:
        text (str): Free text potentially containing prerequisites.
        
    Returns:
        list[str]: A list of unique formatted normalized course IDs.
    """
    prereqs = []
    # Look for patterns like "MATH 251Z", "CS 211", "BI 221Z"
    pattern = r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]*)\b'
    matches = re.findall(pattern, text)
    for subj, num in matches:
        prereqs.append(f"{subj}{num}")
    return list(set(prereqs))

def extract_equivalents(text):
    """
    Extract equivalent courses from 'Equivalent to:' line.
    
    Args:
        text (str): Free text potentially containing course equivalents.
        
    Returns:
        list[str]: A list of unique formatted course ID strings.
    """
    equivs = []
    if "Equivalent to:" in text:
        equiv_section = text.split("Equivalent to:")[-1].split("\n")[0]
        pattern = r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]*)\b'
        matches = re.findall(pattern, equiv_section)
        for subj, num in matches:
            equivs.append(f"{subj}{num}")
    return list(set(equivs))

def extract_tags(text):
    """
    Extract recognized tag keywords like 'Science Area' or 'BS Math'.
    
    Args:
        text (str): Block of text containing the course description.
        
    Returns:
        list[str]: A list of internal tag identifiers mapped correctly.
    """
    tags = []
    tag_patterns = [
        ("science_area", r"Science Area"),
        ("bs_math", r"BS Math"),
        ("arts_letters_area", r"Arts Letters Area"),
        ("social_science_area", r"Social Science Area"),
        ("cultural_literacy_global", r"Cultural Literacy: Global"),
        ("cultural_literacy_us", r"Cultural Literacy: US"),
    ]
    for tag_id, pattern in tag_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            tags.append(tag_id)
    return tags

def parse_course_block(block, subject_code):
    """
    Parse a single course block into a dictionary with metadata keys.
    
    Args:
        block (str): Multi-line course description block string.
        subject_code (str): Course subject code identifier.
        
    Returns:
        dict: The parsed course properties correctly modeled.
    """
    lines = block.strip().split('\n')
    if not lines:
        return None
    
    # First line should be: "SUBJ NUMBER. Title. CREDITS Credits."
    first_line = lines[0].strip()
    
    # Pattern: SUBJ NUMBER. Title. N Credits. or SUBJ NUMBER. Title. N-M Credits.
    match = re.match(
        rf'^({subject_code})\s*(\d+[A-Z]*)\.\s*(.+?)\.\s*([\d,-]+)\s*[Cc]redit',
        first_line
    )
    
    if not match:
        # Try alternate pattern without period after title
        match = re.match(
            rf'^({subject_code})\s*(\d+[A-Z]*)\.\s*(.+?)\s*([\d,-]+)\s*[Cc]redit',
            first_line
        )
    
    if not match:
        return None
    
    subj = match.group(1)
    number_str = match.group(2)
    title = match.group(3).strip().rstrip('.')
    credits_str = match.group(4)
    
    # Parse number (remove letter suffix for level calculation)
    number = int(re.match(r'(\d+)', number_str).group(1))
    level = (number // 100) * 100
    
    credits, credit_range = parse_credits(credits_str)
    
    # Join remaining text for parsing
    full_text = '\n'.join(lines[1:]) if len(lines) > 1 else ""
    
    # Extract prereqs from Requisites line
    prereqs = []
    if "Prereq:" in full_text or "Requisites:" in full_text:
        prereqs = extract_prereqs(full_text)
    
    # Extract equivalents
    equivalents = extract_equivalents(full_text)
    
    # Extract tags
    tags = extract_tags(full_text)
    
    # Build notes (description + requisites)
    notes = ""
    desc_lines = []
    for line in lines[1:]:
        line = line.strip()
        if line.startswith("Requisites:") or line.startswith("Prereq:"):
            notes = line
            break
        if line.startswith("Additional Information:"):
            break
        if line.startswith("Repeatable"):
            continue
        if line.startswith("Equivalent to:"):
            continue
        if line and not re.match(r'^--\s*\d+\s*of\s*\d+\s*--$', line):
            if not re.match(r'^\d+\s+[A-Z]', line):  # Skip page headers
                desc_lines.append(line)
    
    course = {
        "id": f"{subj}{number_str}",
        "subject": subj,
        "number": number,
        "credits": credits,
        "level": level,
        "tags": tags,
        "prereqs": prereqs,
        "title": title,
        "notes": notes if notes else None,
        "equivalents": equivalents if equivalents else None,
    }
    
    if credit_range:
        course["credit_range"] = credit_range
    
    # Clean up None values
    course = {k: v for k, v in course.items() if v is not None and v != []}
    
    return course

def parse_subject_section(text, subject_code):
    """
    Parse all courses cleanly from a broader continuous subject text section.
    
    Args:
        text (str): Aggregated subject module string.
        subject_code (str): The subject code the courses fall under.
        
    Returns:
        list[dict]: Output dictionaries mapped to the contained parsed courses.
    """
    courses = []
    
    # Split by course pattern
    pattern = rf'({subject_code}\s*\d+[A-Z]*\.)'
    parts = re.split(pattern, text)
    
    # Reassemble course blocks
    i = 1
    while i < len(parts) - 1:
        course_header = parts[i]
        course_body = parts[i + 1] if i + 1 < len(parts) else ""
        
        # Find where the next course starts or section ends
        next_course = re.search(rf'{subject_code}\s*\d+[A-Z]*\.', course_body)
        if next_course:
            course_body = course_body[:next_course.start()]
        
        block = course_header + course_body
        course = parse_course_block(block, subject_code)
        if course:
            # Check for duplicate IDs
            if not any(c['id'] == course['id'] for c in courses):
                courses.append(course)
        
        i += 2
    
    return courses

def main():
    """
    Template CLI entrypoint indicating generation practices for creating
    custom manual catalogue data dumps into standard locations.
    """
    # Define subjects and their raw text (you'd read from PDF in practice)
    # For now, this is a template - the actual parsing would read from PDF
    
    output_dir = Path(__file__).parent.parent / "data" / "catalogs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    print("This script is a template. Use parse_subject_from_text() function")
    print("with actual PDF text to generate catalog JSON files.")

if __name__ == "__main__":
    main()
