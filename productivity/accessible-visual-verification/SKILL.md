---
name: accessible-visual-verification
description: Verify doc page bounds for blind users via rendered pages.
version: 1.0.0
author: Hermes curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [accessibility, blind, screen-reader, vision, pdf, verification]
    category: productivity
    related_skills: [pdf, ocr-and-documents]
---

# Accessible Visual Verification

## When to Use
The user is blind or otherwise cannot visually inspect a document (PDF, scanned booklet, image set) to confirm where content starts/stops — e.g. "split this notation/score/report into per-item files, but I can't see reliably where each item begins/ends with my screen reader." This class of task recurs anywhere a sighted-assistance step (find page boundaries, confirm a figure, check layout) is being delegated to the agent instead of the user's own eyes.

Do NOT silently substitute your own visual judgment as ground truth and hand back files with no explanation — the user has no independent way to catch a mistake unless you show your reasoning and evidence.

## Core Procedure
1. **Find an authoritative index first.** Before rendering anything, extract text (`pdf_read.py --text` or equivalent) and look for a table of contents, index, or printed page-number scheme. This is the ground truth to cross-check vision output against — never rely on vision alone if a text-based index exists.
2. **Render pages to images** at a modest DPI (100 is enough for layout/title recognition; use 300 only if fine text must be read) — e.g. `pdf_page_image.py --pages 1-N --dpi 100 --out-dir /tmp/preview/`.
3. **Verify BOTH ends of every extracted range with `vision_analyze`, not just the start:**
   - Confirm the *title/opening* page: title text, printed page number, matches the index.
   - Confirm the *closing* page: look for a double bar line / "Fine" / "Amen" / trailing whitespace / next title NOT yet appearing — i.e. explicit evidence the content actually ends there and doesn't spill onto the next page. A page that looks like a plausible ending can still be a false stop (e.g. mid-piece climax with rallentando but no final barline) — the "no closing evidence found" case must be re-checked on the following page before you trust the boundary.
   - Cross-check the printed page number embedded in the graphic against the index's stated number, not just against the PDF's own 1-based page count (front matter/covers often shift them out of sync).
4. **Batch the vision_analyze calls** for independent pages in the same turn — there's no dependency between checking page 6 vs page 17, so don't serialize one call per turn.
5. **Report your evidence, not just the deliverable.** Give the user the explicit page-range-to-item mapping you used (both PDF page numbers and printed/index page numbers if they differ), and name what you deliberately excluded (covers, license pages, blank pages) and why. This lets the user or a sighted third party spot-check your work without having to re-derive it themselves.
6. **Flag genuine ambiguity instead of guessing.** If a boundary can't be confirmed (no title, no closing cue, conflicting index), say so explicitly rather than picking the more plausible split and presenting it as fact.

## Pitfalls
- Trusting one vision_analyze call per range boundary is not enough — a model describing "this looks like an ending" from cues like rallentando/diminuendo can be wrong when the actual double bar line is on the next page. Always get explicit confirmation of a terminal marker (double bar, "Fine", blank system) or check one page further.
- Printed/booklet page numbers frequently differ from raw PDF page indices (cover pages, license pages, back matter). State both when reporting ranges.
- Don't ask the user "does page X look right?" — they can't check that themselves; that defeats the point of the task. Instead cite the concrete textual/graphical evidence you used (index entry, title match, terminal marker).

## Environment note
If the local `pdf` skill's helper scripts fail with "no module named pypdf"/pip missing on a PEP-668-managed system, don't fight it: `uv venv .venv` inside the skill dir, `uv pip install --python .venv/bin/python pypdf reportlab pdfplumber pypdfium2`, then run scripts as `.venv/bin/python scripts/pdf_xxx.py`. If plain `python3 -m venv` errors with "ensurepip is not available", `sudo apt-get install -y python3.NN-venv` (matching installed Python) then retry `uv venv`.
