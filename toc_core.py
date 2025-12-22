# toc_core.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import os
from dataclasses import dataclass
from typing import List, Optional

import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =========================
# Data model
# =========================

@dataclass
class TocItem:
  title: str
  orig_page_1based: int
  final_page_1based: int
  level: int = 1   # 0=chapter, 1=poem


# =========================
# Text helpers
# =========================

def normalize_line(s: str) -> str:
  s = s.strip()
  s = re.sub(r"\s+", " ", s)
  return s


def page_lines(doc: fitz.Document, page_index: int) -> List[str]:
  text = doc[page_index].get_text("text") or ""
  lines = [normalize_line(l) for l in text.splitlines()]
  return [l for l in lines if l]


# =========================
# TOC extraction
# =========================

def find_toc_page_index(doc: fitz.Document) -> int:
  for i in range(doc.page_count):
    txt = doc[i].get_text("text") or ""
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
    if re.fullmatch(r"\d+", l):
      continue
    titles.append(l)

  titles = [t for t in titles if t and t.lower() != "tartalom"]
  if not titles:
    raise RuntimeError("Extracted 0 TOC titles from 'Tartalom' page.")
  return titles


# =========================
# Chapter detection
# =========================

def is_chapter_title_page(doc: fitz.Document, page_index: int, title: str) -> bool:
  lines = [
    l.strip()
    for l in (doc[page_index].get_text("text") or "").splitlines()
    if l.strip()
  ]
  return len(lines) <= 3 and any(l == title for l in lines)


# =========================
# Title → page resolution
# =========================

def find_title_occurrence_ordered(
  doc: fitz.Document,
  titles: List[str],
  start_search_page_index: int = 0
) -> List[TocItem]:

  items: List[TocItem] = []
  cursor_page = start_search_page_index

  for t in titles:
    pattern = re.escape(t)
    found_page: Optional[int] = None

    for p in range(cursor_page, doc.page_count):
      txt = doc[p].get_text("text") or ""
      if re.search(rf"(?m)^\s*{pattern}\s*$", txt):
        found_page = p
        break
      if re.search(pattern, txt):
        found_page = p
        break

    if found_page is None:
      raise RuntimeError(f"Could not find title in PDF: {t!r}")

    level = 0 if is_chapter_title_page(doc, found_page, t) else 1

    items.append(
      TocItem(
        title=t,
        orig_page_1based=found_page + 1,
        final_page_1based=-1,
        level=level,
      )
    )

    cursor_page = found_page + 1

  return items


# =========================
# Fonts
# =========================

def register_eb_garamond():
  base = os.path.join(os.path.dirname(__file__), "fonts")
  reg = os.path.join(base, "EBGaramond-Regular.ttf")
  med = os.path.join(base, "EBGaramond-Medium.ttf")

  if os.path.exists(reg) and os.path.exists(med):
    pdfmetrics.registerFont(TTFont("EBGaramond", reg))
    pdfmetrics.registerFont(TTFont("EBGaramond-Medium", med))
    return "EBGaramond", "EBGaramond-Medium"

  tnr = r"C:\Windows\Fonts\times.ttf"
  tnr_b = r"C:\Windows\Fonts\timesbd.ttf"
  if os.path.exists(tnr) and os.path.exists(tnr_b):
    pdfmetrics.registerFont(TTFont("TOC-Regular", tnr))
    pdfmetrics.registerFont(TTFont("TOC-Medium", tnr_b))
    return "TOC-Regular", "TOC-Medium"

  raise RuntimeError("No suitable TTF font found (EB Garamond recommended).")


# =========================
# Drawing helpers
# =========================

def draw_dot_leader(
  c: canvas.Canvas,
  x1: float,
  x2: float,
  y: float,
  font: str,
  size: float
):
  if x2 <= x1:
    return

  dot_w = pdfmetrics.stringWidth(".", font, size)
  step = dot_w * 1.35
  x = x1

  c.setFont(font, size)
  while x < x2:
    c.drawString(x, y, ".")
    x += step


# =========================
# TOC rendering
# =========================

def render_toc_pdf(
  toc_items: List[TocItem],
  out_path: str,
  page_size,
  title: str = "Tartalom"
):
  font_reg, font_med = register_eb_garamond()

  w, h = page_size
  c = canvas.Canvas(out_path, pagesize=page_size)

  left = 22 * mm
  right = w - 22 * mm
  top = h - 25 * mm
  bottom = 30 * mm

  y = top

  c.setFont(font_med, 18)
  c.drawCentredString(w / 2, y, title)
  y -= 12 * mm

  poem_indent = 10 * mm
  page_gap = 6 * mm
  leader_gap_after_text = 3 * mm

  for item in toc_items:
    is_chapter = item.level == 0

    if is_chapter:
      y -= 2.5 * mm
      f, fs, indent, row_h = font_med, 12.5, 0, 7.2 * mm
    else:
      f, fs, indent, row_h = font_reg, 11.5, poem_indent, 6.2 * mm

    if y < bottom:
      c.showPage()
      y = top
      c.setFont(font_med, 18)
      c.drawCentredString(w / 2, y, title)
      y -= 12 * mm

    text_x = left + indent
    page_str = str(item.final_page_1based)

    text_w = pdfmetrics.stringWidth(item.title, f, fs)
    page_w = pdfmetrics.stringWidth(page_str, f, fs)

    page_x = right - page_w
    leader_start = text_x + text_w + leader_gap_after_text
    leader_end = page_x - page_gap

    c.setFont(f, fs)
    c.drawString(text_x, y, item.title)
    c.drawString(page_x, y, page_str)
    draw_dot_leader(c, leader_start, leader_end, y, f, fs)

    y -= row_h

  c.save()
