#!/usr/bin/env python3
"""
File: parse_all_catalogs.py
Purpose: Parse all courses from UO_ALL_CLASSES.pdf text dumps and generate 
         JSON catalog files containing parsed course metadata for degree audits.
Authors: Daniel Asiamah

System: Better-UO-Scheduler (Quackademics)
  Run from the backend directory: python deg_guide/scripts/parse_all_catalogs.py
"""
import json
import re
import sys
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
    match = re.match(r'(\d+)-(\d+)', credits_str.strip())
    if match:
        min_c, max_c = int(match.group(1)), int(match.group(2))
        default = 4 if max_c >= 4 else max_c
        return default, {"min": min_c, "max": max_c, "default": default}
    
    match = re.match(r'(\d+)', credits_str.strip())
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
    pattern = r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]*)\b'
    matches = re.findall(pattern, text)
    for subj, num in matches:
        prereqs.append(f"{subj}{num}")
    return list(set(prereqs))

def extract_equivalents(lines):
    """
    Extract equivalent courses from 'Equivalent to:' lines.
    
    Args:
        lines (list[str]): Lines of text corresponding to a course description.
        
    Returns:
        list[str]: A list of unique normalized course IDs that count as equivalents.
    """
    equivs = []
    for line in lines:
        if "Equivalent to:" in line:
            pattern = r'\b([A-Z]{2,4})\s*(\d{3}[A-Z]*)\b'
            matches = re.findall(pattern, line)
            for subj, num in matches:
                equivs.append(f"{subj}{num}")
    return list(set(equivs))

def extract_tags(lines):
    """
    Extract recognized tag keywords like 'Science Area' or 'BS Math'.
    
    Args:
        lines (list[str]): Lines of text containing the course description block.
        
    Returns:
        list[str]: A list of internal tag identifiers mapped correctly.
    """
    tags = []
    full_text = '\n'.join(lines)
    tag_patterns = [
        ("science_area", r"Science Area"),
        ("bs_math", r"BS Math"),
        ("arts_letters_area", r"Arts Letters Area"),
        ("social_science_area", r"Social Science Area"),
    ]
    for tag_id, pattern in tag_patterns:
        if re.search(pattern, full_text, re.IGNORECASE):
            tags.append(tag_id)
    return tags

def parse_subject_from_text(text_lines, subject_code, subject_name):
    """
    Parse all courses belonging to a specific subject out of text lines.
    
    Args:
        text_lines (list[str]): Lines of text covering the specific subject.
        subject_code (str): The common code for a subject (e.g., 'CS').
        subject_name (str): The full subject name.
        
    Returns:
        list[dict]: A list of dictionary objects tracking parsed course metadata.
    """
    courses = []
    
    # Join lines and split by course pattern
    full_text = '\n'.join(text_lines)
    
    # Pattern to match course headers: SUBJ NNN[L]. Title. N[-M] Credit[s].
    course_pattern = rf'({subject_code}\s*\d+[A-Z]?[L]?)\.\s*([^.]+(?:\.[^.]+)*?)\.\s*(\d+(?:-\d+)?)\s*[Cc]redit'
    
    matches = list(re.finditer(course_pattern, full_text))
    
    for i, match in enumerate(matches):
        try:
            course_id_raw = match.group(1).replace(' ', '')
            title = match.group(2).strip()
            credits_str = match.group(3)
            
            # Extract subject and number
            num_match = re.search(r'(\d+)', course_id_raw)
            if not num_match:
                continue
            number = int(num_match.group(1))
            level = (number // 100) * 100
            
            credits, credit_range = parse_credits(credits_str)
            
            # Get the text block for this course (until next course or end)
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            course_block = full_text[start_pos:end_pos]
            block_lines = course_block.split('\n')
            
            # Extract prereqs from Requisites lines
            prereqs = []
            notes = None
            for line in block_lines:
                if "Prereq:" in line or "Requisites:" in line:
                    prereqs = extract_prereqs(line)
                    notes = line.strip()
                    break
            
            # Extract equivalents and tags
            equivalents = extract_equivalents(block_lines)
            tags = extract_tags(block_lines)
            
            course = {
                "id": course_id_raw,
                "subject": subject_code,
                "number": number,
                "credits": credits,
                "level": level,
                "tags": tags if tags else [],
                "prereqs": prereqs if prereqs else [],
                "title": title[:100] if len(title) > 100 else title
            }
            
            if credit_range:
                course["credit_range"] = credit_range
            if notes:
                course["notes"] = notes[:200] if len(notes) > 200 else notes
            if equivalents:
                course["equivalents"] = equivalents
            
            # Check for duplicate IDs
            if not any(c['id'] == course['id'] for c in courses):
                courses.append(course)
                
        except Exception as e:
            print(f"Error parsing course: {e}")
            continue
    
    return courses

def find_subject_sections(lines):
    """
    Find all subject sections in a block of PDF text.
    
    Args:
        lines (list[str]): Complete text line blocks from the catalogue dump.
        
    Returns:
        dict: Values mapping subject codes to sub-dictionaries with code, 
              name, and related text lines.
    """
    sections = {}
    current_subject = None
    current_code = None
    current_lines = []
    
    # Pattern for subject headers: "Subject Name (CODE)" followed by "Courses" on next line
    subject_pattern = r'^([A-Za-z\s,&]+)\s*\(([A-Z]{2,4})\)\s*$'
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if current_subject:
                current_lines.append('')
            continue
            
        # Skip page markers
        if re.match(r'^--\s*\d+\s*of\s*\d+\s*--$', line):
            continue
        if re.match(r'^\d+\s+[A-Z]', line):  # Page headers like "750 Chemistry (CH)"
            continue
        if re.match(r'^\d{4}-\d{4}\s+\d+$', line):  # Year page numbers
            continue
            
        match = re.match(subject_pattern, line)
        if match:
            # Save previous subject
            if current_subject and current_lines:
                sections[current_code] = {
                    'name': current_subject,
                    'code': current_code,
                    'lines': current_lines
                }
            
            current_subject = match.group(1).strip()
            current_code = match.group(2)
            current_lines = []
        elif current_subject:
            current_lines.append(line)
    
    # Save last subject
    if current_subject and current_lines:
        sections[current_code] = {
            'name': current_subject,
            'code': current_code,
            'lines': current_lines
        }
    
    return sections

def main():
    """
    CLI script entrypoint that parses all subjects using a text source
    and writes them individually into separate internal JSON files.
    """
    if len(sys.argv) < 2:
        print("Usage: python parse_all_catalogs.py <path_to_pdf_text>")
        print("  The PDF text should be extracted to a text file first.")
        print("  Or use: python parse_all_catalogs.py --sample to see sample output")
        return
    
    output_dir = Path(__file__).parent.parent / "data" / "catalogs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Skip these subjects (already have catalogs)
    skip_subjects = {'CS', 'MATH', 'PHYS', 'BI', 'ERTH', 'CH', 'PHIL', 'WR', 'DSCI', 'STAT'}
    
    if sys.argv[1] == '--sample':
        print("Sample mode: would parse subjects from PDF")
        return
    
    # Read the PDF text file
    pdf_text_path = sys.argv[1]
    print(f"Reading {pdf_text_path}...")
    
    with open(pdf_text_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove line number prefixes if present
    cleaned_lines = []
    for line in lines:
        # Remove line number prefix (e.g., "  5405|")
        match = re.match(r'^\s*\d+\|(.*)$', line)
        if match:
            cleaned_lines.append(match.group(1))
        else:
            cleaned_lines.append(line.rstrip())
    
    print(f"Read {len(cleaned_lines)} lines")
    
    # Find all subject sections
    print("Finding subject sections...")
    sections = find_subject_sections(cleaned_lines)
    print(f"Found {len(sections)} subjects")
    
    # Parse each subject
    for code, section in sections.items():
        if code in skip_subjects:
            print(f"Skipping {code} (already have catalog)")
            continue
        
        print(f"Parsing {section['name']} ({code})...")
        courses = parse_subject_from_text(section['lines'], code, section['name'])
        
        if courses:
            output_file = output_dir / f"{code.lower()}_catalog.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(courses, f, indent=2)
            print(f"  Wrote {len(courses)} courses to {output_file.name}")
        else:
            print(f"  No courses found for {code}")
    
    print("Done!")

if __name__ == "__main__":
    main()
