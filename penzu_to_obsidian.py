"""
penzu_to_obsidian.py
--------------------
Converts the posts.json produced by penzu_export.py into individual
Markdown files ready to drop into an Obsidian vault.

Usage:
    python penzu_to_obsidian.py

Expects posts.json in the same directory.
Writes .md files to ./obsidian_notes/
"""

import json
import os
import re
from pathlib import Path


INPUT_FILE = "posts.json"
OUTPUT_DIR = "obsidian_notes"


def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in filenames across platforms."""
    return re.sub(r'[\\/:*?"<>|]', "", name).strip()


def convert():
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print(f"ERROR: {INPUT_FILE} not found. Run penzu_export.py first.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Track filenames to avoid collisions (multiple entries on same date with same title)
    used_filenames: dict[str, int] = {}

    for post in posts:
        date_str = (post.get("created_at") or "0000-00-00")[:10]
        title = post.get("title") or "Untitled"
        safe_title = sanitize_filename(title)
        base_filename = f"{date_str} {safe_title}"

        # Handle duplicate filenames
        if base_filename in used_filenames:
            used_filenames[base_filename] += 1
            filename = f"{base_filename} ({used_filenames[base_filename]}).md"
        else:
            used_filenames[base_filename] = 0
            filename = f"{base_filename}.md"

        tags = post.get("tags", [])
        plaintext = post.get("plaintext") or ""

        # Build YAML frontmatter
        frontmatter_tags = "\n".join(f"  - {t}" for t in tags) if tags else ""
        frontmatter = f"---\ndate: {date_str}\n"
        if frontmatter_tags:
            frontmatter += f"tags:\n{frontmatter_tags}\n"
        frontmatter += "source: penzu\n---\n"

        # Inline tags for Obsidian tag search (optional but useful)
        tag_line = "  ".join(f"#{t}" for t in tags) if tags else ""

        content = frontmatter
        content += f"\n# {title}\n\n"
        if tag_line:
            content += f"{tag_line}\n\n"
        content += plaintext

        file_path = output_path / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"Done! {len(posts)} notes written to '{OUTPUT_DIR}/'")
    print("Open that folder as your Obsidian vault, or copy its contents into an existing vault.")


if __name__ == "__main__":
    convert()
