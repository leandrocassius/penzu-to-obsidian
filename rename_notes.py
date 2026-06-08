"""
rename_notes.py
---------------
Renames Penzu-exported Obsidian note files in a given folder.

Rules:
- Filenames always start with YYYY-MM-DD, which is stripped.
- If the remainder starts with a 3-letter weekday abbreviation (Mon, Tue, etc.)
  with or without a trailing period and any junk after it, the file is renamed to:
      "Notes from {Full Weekday}, {long date}.md"
  e.g. "2019-11-20 Wed. 11202019.md" → "Notes from Wednesday, 20th of November, 2019.md"
- If the remainder is a real title, the file is renamed to just the title:
  e.g. "2019-11-24 Places I Would Like to Visit.md" → "Places I Would Like to Visit.md"

Usage:
    python rename_notes.py
    
    By default operates on the current directory.
    To target a specific folder, set NOTES_DIR below.
"""

import os
import re
from pathlib import Path
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
NOTES_DIR = r"Path/to/your/folder"
DRY_RUN = True  # Set to False to actually rename. True just prints what would happen.
# ──────────────────────────────────────────────────────────────────────────────

WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

WEEKDAY_FULL = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
    "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
}

MONTH_FULL = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}


def ordinal(n: int) -> str:
    """Return ordinal string for a number, e.g. 1 → '1st', 20 → '20th'."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def long_date(dt: datetime) -> str:
    """Format a datetime as e.g. '20th of November, 2019'."""
    return f"{ordinal(dt.day)} of {MONTH_FULL[dt.month]}, {dt.year}"


def full_weekday(dt: datetime) -> str:
    """Return the full weekday name for a datetime."""
    return dt.strftime("%A")  # Monday, Tuesday, etc.


def new_name(filename: str) -> str | None:
    """
    Given a filename (without directory), return the new filename,
    or None if no rename is needed.
    """
    stem = Path(filename).stem   # filename without .md
    suffix = Path(filename).suffix

    # Must start with YYYY-MM-DD
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})\s+(.*)", stem)
    if not date_match:
        return None

    date_str = date_match.group(1)   # e.g. "2019-11-20"
    remainder = date_match.group(2).strip()  # everything after the date

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

    # Detect and strip a trailing (n) suffix, e.g. "(1)", "(2)"
    # We'll re-attach it at the end
    trailing_suffix = ""
    trailing_match = re.search(r"\s*(\(\d+\))$", remainder)
    if trailing_match:
        trailing_suffix = f" {trailing_match.group(1).strip()}"
        remainder = remainder[:trailing_match.start()].strip()

    # Check if remainder starts with a 3-letter weekday abbreviation
    dow_match = re.match(r"^([A-Za-z]{3})\.?\s*.*$", remainder)
    if dow_match and dow_match.group(1).lower() in WEEKDAYS:
        new_stem = f"Notes from {full_weekday(dt)}, {long_date(dt)}{trailing_suffix}"
    else:
        # It's a real title — just strip the date prefix
        new_stem = f"{remainder}{trailing_suffix}"

    if new_stem == stem:
        return None  # nothing changed

    return f"{new_stem}{suffix}"


def run():
    folder = Path(NOTES_DIR)
    if not folder.exists():
        print(f"ERROR: Folder not found: {folder}")
        return

    md_files = list(folder.glob("*.md"))
    if not md_files:
        print("No .md files found in the folder.")
        return

    renames = []
    skipped = 0

    for file in sorted(md_files):
        result = new_name(file.name)
        if result is None:
            skipped += 1
            continue
        renames.append((file, folder / result))

    print(f"Files to rename: {len(renames)}  |  Skipped (no change): {skipped}\n")

    for old_path, new_path in renames:
        print(f"  {old_path.name}")
        print(f"→ {new_path.name}\n")

    if DRY_RUN:
        print("DRY RUN — no files were changed. Set DRY_RUN = False to apply.")
        return

    # Resolve collisions: if two files would get the same name,
    # append (1), (2), etc. to disambiguate.
    # Also accounts for files that already exist in the folder.
    seen_names: set[str] = set()

    def resolve_collision(new_path: Path) -> Path:
        """If new_path conflicts with a seen name, increment a (n) suffix until unique."""
        candidate = new_path
        stem = new_path.stem
        suffix = new_path.suffix

        # Strip any existing trailing (n) from the stem
        base_stem = re.sub(r"\s*\(\d+\)$", "", stem).strip()
        counter = 1

        while candidate.name in seen_names or (candidate.exists() and candidate not in [o for o, _ in renames]):
            candidate = new_path.parent / f"{base_stem} ({counter}){suffix}"
            counter += 1

        return candidate

    resolved_renames = []
    for old_path, new_path in renames:
        final_path = resolve_collision(new_path)
        if final_path.name != new_path.name:
            print(f"COLLISION RESOLVED: {new_path.name} → {final_path.name}")
        seen_names.add(final_path.name)
        resolved_renames.append((old_path, final_path))

    for old_path, new_path in resolved_renames:
        old_path.rename(new_path)

    print(f"Done. {len(resolved_renames)} files renamed.")


if __name__ == "__main__":
    run()
