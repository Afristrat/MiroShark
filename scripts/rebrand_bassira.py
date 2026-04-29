"""
One-shot rebrand script: MiroShark → Bassira (frontend only).
Preserves 3 technical strings :
  - aaronjmars/MiroShark  (external repo URL)
  - miroshark.app         (placeholder URL example)
  - /miroshark-nobg.png   (logo asset filename — image still has old brand)
Run from project root: `python scripts/rebrand_bassira.py`
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIRS = [
    ROOT / "frontend" / "src",
    ROOT / "frontend" / "public",
]
SINGLE_FILES = [
    ROOT / "frontend" / "index.html",
]

# Regex: protect specific strings, then replace everything else
# Use sentinels to round-trip the protected substrings.
PROTECTED = [
    ("aaronjmars/MiroShark", "\x00P0\x00"),
    ("miroshark.app",        "\x00P1\x00"),
    ("miroshark-nobg.png",   "\x00P2\x00"),
]

# Replacements applied in order (longest/most-specific first).
REPLACEMENTS = [
    ("MIROSHARK",   "BASSIRA"),
    ("MiroShark",   "Bassira"),
    ("miroshark",   "bassira"),
    ("ميروشارك",    "بصيرة"),
]

EXTENSIONS = {".vue", ".js", ".ts", ".json", ".html", ".css", ".md"}

def process(text: str) -> tuple[str, int]:
    # Stash protected
    for orig, sentinel in PROTECTED:
        text = text.replace(orig, sentinel)
    # Apply replacements
    total = 0
    for old, new in REPLACEMENTS:
        new_text, n = re.subn(re.escape(old), new, text)
        total += n
        text = new_text
    # Restore protected
    for orig, sentinel in PROTECTED:
        text = text.replace(sentinel, orig)
    return text, total

def collect_files():
    out = list(SINGLE_FILES)
    for d in TARGET_DIRS:
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in EXTENSIONS:
                out.append(p)
    return out

def main():
    total_files_changed = 0
    total_replacements = 0
    for path in collect_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_text, n = process(text)
        if n > 0 and new_text != text:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            rel = path.relative_to(ROOT)
            print(f"  {n:3d}  {rel}")
            total_files_changed += 1
            total_replacements += n
    print(f"\n→ {total_files_changed} files changed, {total_replacements} replacements")

if __name__ == "__main__":
    main()
