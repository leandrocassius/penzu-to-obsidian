# penzu-to-obsidian

Export your Penzu journal entries as individual Markdown files, ready to import into [Obsidian](https://obsidian.md).

## Background

This is a Python rewrite of [@mirontoli](https://gist.github.com/mirontoli/a3dd9d9618477f1ddc5311c509bb8bab)'s `penzu-export.js`. Full credit for the original approach goes to them — the core mechanic (attaching to a running Chrome session and intercepting Penzu's internal API responses) is their idea.

**Why rewrite it in Python?**

- The original depends on `axios` (npm), which was [compromised in March 2026](https://www.esentire.com/security-advisories/axios-npm-packages-compromised) via a supply chain attack.
- Python + Playwright avoids the npm ecosystem risk entirely.
- Easier to run as a one-off script — no Node.js project setup required.

---

## How it works

Penzu's export feature (Pro only) produces a single PDF — not useful if you want individual, structured files. There is no official data export API.

This tool attaches to your already-logged-in Chrome session via the Chrome DevTools Protocol, intercepts Penzu's internal API responses as you navigate through entries, and saves the structured data locally. It then converts those entries to `.md` files with YAML frontmatter that Obsidian understands.

---

## Requirements

- Python 3.8+
- Google Chrome installed
- A Penzu account (free or Pro)

Install dependencies:

```bash
pip install playwright
playwright install chromium
```

---

## Usage

### Step 1 — Start Chrome with remote debugging

**Windows (PowerShell):**
```powershell
Start-Process Chrome -ArgumentList '--remote-debugging-port=9222'
```

**Mac:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**Linux:**
```bash
google-chrome --remote-debugging-port=9222
```

### Step 2 — Log in to Penzu

In that Chrome window, log in to your Penzu account and navigate to your **most recent** journal entry. The URL will look like:

```
https://penzu.com/journals/1234567/89012345
```

Note the two numbers — that's your `JOURNAL_ID` and `MOST_RECENT_POST_ID`.

### Step 3 — Configure the script

Open `penzu_export.py` and update these lines:

```python
JOURNAL_ID = "your_journal_id"
MOST_RECENT_POST_ID = "your_most_recent_post_id"
```

### Step 4 — Run the exporter

```bash
python penzu_export.py
```

The script walks backwards through all your entries, respecting rate limits (minimum 10s delay between requests). It saves everything to `posts.json`.

### Step 5 — Convert to Obsidian Markdown

```bash
python penzu_to_obsidian.py
```

This reads `posts.json` and writes individual `.md` files to `./obsidian_notes/`, one per entry, named like:

```
2021-03-15 My entry title.md
```

Each file includes YAML frontmatter with the date, tags, and source, plus inline `#tags` for Obsidian's tag search.

### Step 6 — (Optional) Clean up filenames

If your Penzu entries used auto-generated date-based titles like `Wed. 11202019` or `Tue 28 Mar, 2023`, the optional `rename_notes.py` script can clean those up into readable names.

Open `rename_notes.py` and set `NOTES_DIR` to the folder containing your notes:

```python
NOTES_DIR = "path/to/your/obsidian_notes"
```

Run it first in dry-run mode (the default) to preview what will change:

```bash
python rename_notes.py
```

When you're happy with the output, set `DRY_RUN = False` and run again to apply.

**What it does:**

| Before | After |
|---|---|
| `2019-11-20 Wed. 11202019.md` | `Notes from Wednesday, 20th of November, 2019.md` |
| `2023-03-28 Tue 28 Mar, 2023.md` | `Notes from Tuesday, 28th of March, 2023.md` |
| `2019-11-24 Places I Would Like to Visit.md` | `Places I Would Like to Visit.md` |

If two entries would produce the same filename, a `(1)`, `(2)` etc. suffix is added automatically.

### Step 7 — Import into Obsidian

Copy the `obsidian_notes/` folder into your Obsidian vault, or open it directly as a new vault.

---

## Notes

- The exporter requires a minimum 10-second delay between requests. Going faster will trigger HTTP 429 rate limiting from Penzu.
- Only `plaintext_body` is captured. If you need rich text / HTML, uncomment `richtext_body` in `penzu_export.py`.
- This was tested on Windows and Mac. Linux should work but is untested.

---

## Credits

Original concept and JavaScript implementation by [@mirontoli](https://gist.github.com/mirontoli/a3dd9d9618477f1ddc5311c509bb8bab).

## License

MIT — see [LICENSE](LICENSE) for details. Original concept by [@mirontoli](https://gist.github.com/mirontoli/a3dd9d9618477f1ddc5311c509bb8bab).
