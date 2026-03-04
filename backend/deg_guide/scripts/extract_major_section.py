#!/usr/bin/env python3
"""
extract_major_section.py

Extract a major (or any section) from a large catalog PDF by locating a start
header pattern and an end header pattern, then exporting:
  - a PDF excerpt (page-exact)
  - optional per-page text dump for downstream parsing/diffing

Requires:
  pip install pdfplumber pypdf

Notes:
- This does NOT OCR. If the PDF is image-only, you'll need OCR first.
- Heuristics are configurable: you can provide explicit start/end regexes,
  or let it infer end by matching common "next section" heading styles.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple, List

import pdfplumber
from pypdf import PdfReader, PdfWriter


@dataclass
class Match:
    page_index: int          # 0-based
    line: str
    score: int


def normalize(s: str) -> str:
    # Normalize weird dashes and whitespace; keep it simple.
    return (
        s.replace("\u2013", "-")
         .replace("\u2014", "-")
         .replace("\u00ad", "")
    )


def iter_page_text(pdf_path: Path) -> Iterable[Tuple[int, str]]:
    """Yield (page_index, text) for each page."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            yield i, normalize(text)


def find_best_page(
    pages: Iterable[Tuple[int, str]],
    start_re: re.Pattern,
    boost_re: Optional[re.Pattern] = None,
) -> Optional[Match]:
    """
    Find the most likely start page by scanning text pages and scoring matches.
    """
    best: Optional[Match] = None
    for idx, text in pages:
        # score by number of start matches + optional boost (e.g. "Major Requirements")
        score = 0
        hits = list(start_re.finditer(text))
        if hits:
            score += 10 * len(hits)
            # prefer earlier occurrences on the page
            first_pos = hits[0].start()
            score += max(0, 1000 - first_pos)

        if boost_re and boost_re.search(text):
            score += 50

        if score > 0:
            # pick a representative line
            snippet = ""
            for line in text.splitlines():
                if start_re.search(line):
                    snippet = line.strip()
                    break
            candidate = Match(page_index=idx, line=snippet, score=score)
            if best is None or candidate.score > best.score:
                best = candidate
    return best


def build_heading_regexes(major: str) -> Tuple[re.Pattern, re.Pattern]:
    """
    Default heuristics for UO catalog headings.

    Start: match the exact major phrase as a heading-ish line.
    End: match another heading-ish line that likely starts the next section.
    """
    major_esc = re.escape(major.strip())
    # Start: allow minor variations in whitespace, BA/BS, parentheses, etc.
    start_pat = rf"(?m)^\s*{major_esc}\s*$"

    # End: common UO patterns that indicate a new major/section:
    # - "Minor", "Graduate Programs", "Undergraduate Programs", or a new "(BA/BS)" heading
    # - Any line that looks like "Something (BA/BS)" or "Something (BS)" etc.
    end_pat = (
        r"(?m)^\s*(Undergraduate Programs|Graduate Programs|Minors?|Major\s*-\s*Bachelor|"
        r".+\(\s*BA/BS\s*\)|.+\(\s*BS\s*\)|.+\(\s*BA\s*\))\s*$"
    )

    return re.compile(start_pat, re.IGNORECASE), re.compile(end_pat)


def locate_section(
    pdf_path: Path,
    start_regex: str,
    end_regex: Optional[str],
    search_from_page: int = 0,
    max_pages_forward: int = 80,
) -> Tuple[int, int]:
    """
    Return (start_page_index, end_page_index_inclusive).
    If end_regex is None, infer end by scanning for a likely "next heading" after start.
    """
    start_re = re.compile(start_regex, re.IGNORECASE | re.MULTILINE)
    end_re = re.compile(end_regex, re.IGNORECASE | re.MULTILINE) if end_regex else None

    pages = list(iter_page_text(pdf_path))
    pages = [(i, t) for (i, t) in pages if i >= search_from_page]

    # Boost if the major section contains "Major Requirements" etc. (helps disambiguate)
    boost = re.compile(r"(?i)\bMajor Requirements\b|\bDegree Requirements\b")

    best = find_best_page(pages, start_re, boost_re=boost)
    if not best:
        raise SystemExit(f"Could not find start heading matching: {start_regex}")

    start_idx = best.page_index

    # Find end:
    # Scan forward until we see end heading, but ignore the start page itself for end.
    last_page = min(start_idx + max_pages_forward, pages[-1][0])
    end_idx = last_page

    # If an explicit end regex is provided, use it.
    # Otherwise, use a generic heading matcher but skip matches that are just repeats of the same major heading.
    generic_heading = re.compile(
        r"(?m)^\s*[A-Z][A-Za-z&/\- ,]+(\(\s*BA/BS\s*\)|\(\s*BS\s*\)|\(\s*BA\s*\))\s*$"
    )

    for i in range(start_idx + 1, last_page + 1):
        text = dict(pages).get(i, "")
        if not text.strip():
            continue

        if end_re and end_re.search(text):
            end_idx = i - 1
            break

        if not end_re:
            # generic: stop at the next major-like heading OR big program block markers
            if generic_heading.search(text) or re.search(r"(?m)^\s*Minors?\s*$", text):
                end_idx = i - 1
                break

    if end_idx < start_idx:
        end_idx = start_idx

    return start_idx, end_idx


def export_pdf_pages(
    src_pdf: Path,
    dst_pdf: Path,
    start_idx: int,
    end_idx: int,
) -> None:
    reader = PdfReader(str(src_pdf))
    writer = PdfWriter()
    for i in range(start_idx, end_idx + 1):
        writer.add_page(reader.pages[i])
    dst_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(dst_pdf, "wb") as f:
        writer.write(f)


def export_text_dump(
    src_pdf: Path,
    dst_txt: Path,
    start_idx: int,
    end_idx: int,
) -> None:
    lines: List[str] = []
    with pdfplumber.open(str(src_pdf)) as pdf:
        for i in range(start_idx, end_idx + 1):
            page = pdf.pages[i]
            text = normalize(page.extract_text() or "")
            lines.append(f"\n\n===== PAGE {i+1} =====\n")
            lines.append(text)
    dst_txt.parent.mkdir(parents=True, exist_ok=True)
    dst_txt.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract a major/section from a catalog PDF.")
    ap.add_argument("pdf", type=Path, help="Path to the large catalog PDF")
    ap.add_argument("--major", type=str, default=None,
                    help="Major/section heading to find (e.g., 'Computer Science (BA/BS)')")
    ap.add_argument("--start-regex", type=str, default=None,
                    help="Override: regex to find start")
    ap.add_argument("--end-regex", type=str, default=None,
                    help="Override: regex that indicates start of next section; end will be page before match")
    ap.add_argument("--from-page", type=int, default=1,
                    help="1-based page number to start searching from (default: 1)")
    ap.add_argument("--max-forward", type=int, default=80,
                    help="Max pages to scan after the start page when finding the end (default: 80)")

    ap.add_argument("--outdir", type=Path, default=Path("extracted"),
                    help="Output directory (default: ./extracted)")
    ap.add_argument("--outname", type=str, default=None,
                    help="Base name for outputs (default: sanitized major or 'section')")
    ap.add_argument("--pdf-only", action="store_true",
                    help="Only export PDF excerpt")
    ap.add_argument("--text-only", action="store_true",
                    help="Only export text dump")

    args = ap.parse_args()

    # Resolve PDF path: if not found as given, look in deg_guide/data/records
    records_dir = Path(__file__).resolve().parent.parent / "data" / "records"
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        candidate = records_dir / pdf_path.name
        if candidate.exists():
            args.pdf = candidate
        else:
            raise SystemExit(f"PDF not found: {args.pdf} (also tried {candidate})")
    else:
        args.pdf = pdf_path.resolve()

    if not args.major and not args.start_regex:
        raise SystemExit("Provide --major or --start-regex")

    if args.major and not args.start_regex:
        start_re, end_re_default = build_heading_regexes(args.major)
        start_regex = start_re.pattern
        end_regex = args.end_regex or end_re_default.pattern
    else:
        start_regex = args.start_regex
        end_regex = args.end_regex  # may be None

    start_idx, end_idx = locate_section(
        pdf_path=args.pdf,
        start_regex=start_regex,
        end_regex=end_regex,
        search_from_page=max(0, args.from_page - 1),
        max_pages_forward=args.max_forward,
    )

    # Output names
    base = args.outname
    if not base:
        if args.major:
            base = re.sub(r"[^A-Za-z0-9]+", "_", args.major).strip("_").lower()
        else:
            base = "section"

    out_pdf = args.outdir / f"{base}.pdf"
    out_txt = args.outdir / f"{base}.txt"

    print(f"Found section pages: {start_idx+1} to {end_idx+1} (1-based)")
    if not args.text_only:
        export_pdf_pages(args.pdf, out_pdf, start_idx, end_idx)
        print(f"Wrote PDF excerpt: {out_pdf}")

    if not args.pdf_only:
        export_text_dump(args.pdf, out_txt, start_idx, end_idx)
        print(f"Wrote text dump:  {out_txt}")


if __name__ == "__main__":
    main()