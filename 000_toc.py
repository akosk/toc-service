#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create a new PDF with a generated TOC containing accurate page numbers.

Input:  /mnt/data/vers.pdf
Output: /mnt/data/vers_with_toc.pdf

Strategy:
- Extract TOC titles from the existing "Tartalom" page.
- For each title, find its next occurrence in the document (ordered matching),
  to disambiguate repeated titles (e.g., "Fagyott göröngyök").
- Generate TOC pages with reportlab.
- Insert TOC after page 2 (cover + impresszum), adjust page numbers accordingly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

import fitz  # PyMuPDF
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

INPUT_PDF = "c:\\dev\\vers.pdf"
OUTPUT_PDF = "c:\\dev\\vers_with_toc.pdf"
TOC_TMP_PDF = "c:\\dev\\_generated_toc.pdf"


@dataclass
class TocItem:
  title: str
  orig_page_1based: int
  final_page_1based: int
  level: int = 1   # 0=chapter, 1=poem (default poem)

def normalize_line(s: str) -> str:
  s = s.strip()
  s = re.sub(r"\s+", " ", s)
  return s


def page_lines(doc: fitz.Document, page_index: int) -> List[str]:
  text = doc[page_index].get_text("text") or ""
  lines = [normalize_line(l) for l in text.splitlines()]
  return [l for l in lines if l]


def find_toc_page_index(doc: fitz.Document) -> int:
  # Find the page that contains the "Tartalom" heading.
  for i in range(doc.page_count):
    txt = (doc[i].get_text("text") or "")
    if re.search(r"\bTartalom\b", txt):
      return i
  raise RuntimeError("Could not find a page containing 'Tartalom'.")


def extract_toc_titles(doc: fitz.Document) -> List[str]:
  toc_i = find_toc_page_index(doc)
  lines = page_lines(doc, toc_i)

  titles: List[str] = []
  in_toc = False
  for l in lines:
    if re.fullmatch(r"Tartalom", l):
      in_toc = True
      continue
    if not in_toc:
      continue

    # Drop pure page-number lines, if any
    if re.fullmatch(r"\d+", l):
      continue

    # A TOC item line is typically a title
    titles.append(l)

  # Filter obvious noise (if any)
  titles = [t for t in titles if t and t.lower() != "tartalom"]
  if not titles:
    raise RuntimeError("Extracted 0 TOC titles from 'Tartalom' page.")
  return titles


def find_title_occurrence_ordered(
  doc: fitz.Document,
  titles: List[str],
  start_search_page_index: int = 0
) -> List[TocItem]:
  """
  For each title in titles order, find the next page where that title appears.
  Uses ordered matching to disambiguate duplicates:
    - "Fagyott göröngyök" appears multiple times, so we match the next occurrence
      after the previously matched page.
  """
  items: List[TocItem] = []
  cursor_page = start_search_page_index

  for t in titles:
    pattern = re.escape(t)

    found_page: Optional[int] = None
    for p in range(cursor_page, doc.page_count):
      txt = doc[p].get_text("text") or ""
      # Prefer matching as a full line if possible:
      if re.search(rf"(?m)^\s*{pattern}\s*$", txt):
        found_page = p
        break
      # Fallback: anywhere on the page
      if re.search(pattern, txt):
        found_page = p
        break

    if found_page is None:
      raise RuntimeError(f"Could not find title in PDF: {t!r}")

    level = 0 if is_chapter_title_page(doc, found_page, t) else 1
    items.append(TocItem(title=t, orig_page_1based=found_page + 1, final_page_1based=-1, level=level))

    cursor_page = found_page + 1

  return items


def render_toc_pdf(toc_items, out_path, page_size, title="Tartalom"):
  """
  toc_items: list of objects with:
    - title (str)
    - final_page_1based (int)
    - level (0=chapter, 1=poem)
  """
  font_reg, font_med = register_eb_garamond()

  w, h = page_size
  c = canvas.Canvas(out_path, pagesize=page_size)

  # match your CSS-ish margins: 25mm 22mm 30mm 22mm
  left = 22 * mm
  right = w - 22 * mm
  top = h - 25 * mm
  bottom = 30 * mm

  y = top

  # Title similar to .toc-title
  c.setFont(font_med, 18)
  c.drawCentredString(w / 2, y, title)
  y -= 12 * mm

  # Layout params (tune if needed)
  poem_indent = 10 * mm
  page_gap = 6 * mm             # space between dots and page number
  leader_gap_after_text = 3 * mm
  min_y = bottom

  for item in toc_items:
    is_chapter = getattr(item, "level", 1) == 0

    if is_chapter:
      # extra spacing before chapter blocks (except if first)
      y -= 2.5 * mm
      f = font_med
      fs = 12.5  # close to your body 12.5pt
      indent = 0
      row_h = 7.2 * mm
    else:
      f = font_reg
      fs = 11.5
      indent = poem_indent
      row_h = 6.2 * mm

    if y < min_y:
      c.showPage()
      y = top
      c.setFont(font_med, 18)
      c.drawCentredString(w / 2, y, title)
      y -= 12 * mm

    text_x = left + indent
    page_str = str(item.final_page_1based)

    # Measure widths
    text_w = pdfmetrics.stringWidth(item.title, f, fs)
    page_w = pdfmetrics.stringWidth(page_str, f, fs)

    # Positions
    page_x = right - page_w
    leader_start = text_x + text_w + leader_gap_after_text
    leader_end = page_x - page_gap

    # Draw title
    c.setFont(f, fs)
    c.drawString(text_x, y, item.title)

    # Draw page number
    c.drawString(page_x, y, page_str)

    # Dotted leader
    draw_dot_leader(c, leader_start, leader_end, y, f, fs)

    y -= row_h

  c.save()
  return 1  # if you need page count, compute it externally (or keep your existing logic)

def is_chapter_title_page(doc, page_index: int, title: str) -> bool:
  lines = [l.strip() for l in (doc[page_index].get_text("text") or "").splitlines() if l.strip()]
  if len(lines) <= 3 and any(l.strip() == title for l in lines):
    return True
  return False

def register_eb_garamond():
  base = os.path.join(os.path.dirname(__file__), "fonts")
  reg = os.path.join(base, "EBGaramond-Regular.ttf")
  med = os.path.join(base, "EBGaramond-Medium.ttf")

  # Preferred (project-local)
  if os.path.exists(reg) and os.path.exists(med):
    pdfmetrics.registerFont(TTFont("EBGaramond", reg))
    pdfmetrics.registerFont(TTFont("EBGaramond-Medium", med))
    return "EBGaramond", "EBGaramond-Medium"

  # Fallback: Times New Roman (Unicode, usually present)
  tnr = r"C:\Windows\Fonts\times.ttf"
  tnr_b = r"C:\Windows\Fonts\timesbd.ttf"
  if os.path.exists(tnr) and os.path.exists(tnr_b):
    pdfmetrics.registerFont(TTFont("TOC-Regular", tnr))
    pdfmetrics.registerFont(TTFont("TOC-Medium", tnr_b))
    return "TOC-Regular", "TOC-Medium"

  # Last fallback: DejaVu Serif if present
  dej = r"C:\Windows\Fonts\DejaVuSerif.ttf"
  if os.path.exists(dej):
    pdfmetrics.registerFont(TTFont("TOC-Regular", dej))
    pdfmetrics.registerFont(TTFont("TOC-Medium", dej))
    return "TOC-Regular", "TOC-Medium"

  raise RuntimeError("No suitable TTF font found. Add EB Garamond TTFs under ./fonts.")


def draw_dot_leader(c: canvas.Canvas, x1: float, x2: float, y: float, font: str, size: float):
  """Draw dotted leader between x1..x2 using '.' spaced by its glyph width."""
  if x2 <= x1:
    return
  dot_w = pdfmetrics.stringWidth(".", font, size)
  if dot_w <= 0:
    return
  # Add a little spacing so it looks like classic TOC leaders
  step = dot_w * 1.35
  x = x1
  c.setFont(font, size)
  while x < x2:
    c.drawString(x, y, ".")
    x += step


def register_unicode_font():
  # Prefer a local bundled font if you add it to your repo (recommended)
  # Example: put DejaVuSerif.ttf under ./fonts/
  candidates = [
    os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSerif.ttf"),
    r"C:\Windows\Fonts\DejaVuSerif.ttf",
    r"C:\Windows\Fonts\dejavuserif.ttf",
    r"C:\Windows\Fonts\arial.ttf",  # fallback (less typographic)
  ]
  for p in candidates:
    if os.path.exists(p):
      pdfmetrics.registerFont(TTFont("TOCFont", p))
      return "TOCFont"
  raise RuntimeError("No Unicode TTF font found. Add one to ./fonts (e.g., DejaVuSerif.ttf).")




def main():
  doc = fitz.open(INPUT_PDF)

  # 1) Extract titles from existing TOC
  toc_titles = extract_toc_titles(doc)

  # 2) Match them to original pages (ordered, disambiguates duplicates)
  # Start searching after cover+impresszum to reduce false matches
  items = find_title_occurrence_ordered(doc, toc_titles, start_search_page_index=2)

  # 3) Decide insertion point: after page 2 (0-based index 1)
  # Insert TOC as new pages AFTER impresszum => insertion_index = 2 (0-based)
  insertion_index = doc.page_count  # after pages 0..1

  # 4) We don’t know TOC page count until we render it.
  # First pass: assume 1 page to compute layout, then re-render if page count changes.
  for it in items:
    it.final_page_1based = it.orig_page_1based  # placeholder

  rect = doc[0].rect
  page_size = (rect.width, rect.height)
  toc_pages = render_toc_pdf(items, TOC_TMP_PDF, page_size)



  # 5) Now compute final page numbers with the real toc_pages.
  # Any page >= insertion_index+1 in original shifts by +toc_pages.
  # Original pages are 1-based, insertion after original page 2 => pages >= 3 shift.
  for it in items:
    if it.orig_page_1based >= (insertion_index + 1):
      it.final_page_1based = it.orig_page_1based + toc_pages
    else:
      it.final_page_1based = it.orig_page_1based  # should not happen here, but safe

  # 6) Re-render TOC with correct numbers (toc_pages may remain same; if it changes, re-run once)
  toc_pages2 = render_toc_pdf(items, TOC_TMP_PDF, page_size)
  if toc_pages2 != toc_pages:
    toc_pages = toc_pages2
    for it in items:
      if it.orig_page_1based >= (insertion_index + 1):
        it.final_page_1based = it.orig_page_1based + toc_pages
      else:
        it.final_page_1based = it.orig_page_1based
    render_toc_pdf(items, TOC_TMP_PDF, page_size)

  # 7) Merge: insert TOC into original
  toc_doc = fitz.open(TOC_TMP_PDF)
  out = fitz.open()
  out.insert_pdf(doc)  # whole original
  out.insert_pdf(toc_doc)  # TOC appended

  out.save(OUTPUT_PDF)
  out.close()
  toc_doc.close()
  doc.close()

  print("Wrote:", OUTPUT_PDF)
  print("TOC pages inserted:", toc_pages)
  for it in items:
    print(f"{it.title} -> original {it.orig_page_1based}, final {it.final_page_1based}")


if __name__ == "__main__":
  main()
