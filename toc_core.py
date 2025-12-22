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
# TOC extraction (Scan)
# =========================

def build_toc_from_scan(doc: fitz.Document) -> List[TocItem]:
  items: List[TocItem] = []

  # Start scanning from page index 2 (skipping 0=Cover, 1=Impresszum)
  start_page = 2

  for p in range(start_page, doc.page_count):
    page = doc[p]

    # Get text blocks to analyze font size and content
    blocks = page.get_text("dict")["blocks"]
    text_blocks = [b for b in blocks if b["type"] == 0]

    if not text_blocks:
      continue

    first_block = text_blocks[0]
    if not first_block["lines"]:
      continue

    first_line = first_block["lines"][0]
    if not first_line["spans"]:
      continue

    # Analyze the first span of the first line
    span = first_line["spans"][0]
    size = span["size"]

    # Reconstruct the full title text
    raw_text = "".join(s["text"] for s in first_line["spans"])
    title = normalize_line(raw_text)

    if not title:
      continue

    # Classification based on font size
    # Chapter Title: ~26pt (Level 0)
    # Poem Title: ~18.75pt (Level 1)
    # Body Text: ~12.5pt (Ignore)

    level = -1
    if size > 24:
      level = 0
    elif 16 < size < 24:
      level = 1

    if level != -1:
      items.append(TocItem(
        title=title,
        orig_page_1based=p + 1,
        final_page_1based=-1,
        level=level,
      ))

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
