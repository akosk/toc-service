#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create a new PDF with a generated TOC containing accurate page numbers.

Input:  c:\dev\vers.pdf
Output: c:\dev\vers_with_toc.pdf

Strategy:
- Scan pages for titles (based on font size).
- Generate TOC pages with reportlab.
- Insert TOC after page 2 (cover + impresszum), adjust page numbers accordingly.
"""

from __future__ import annotations

import fitz  # PyMuPDF
from toc_core import build_toc_from_scan, render_toc_pdf

INPUT_PDF = "c:\\dev\\vers.pdf"
OUTPUT_PDF = "c:\\dev\\vers_with_toc.pdf"
TOC_TMP_PDF = "c:\\dev\\_generated_toc.pdf"


def main():
  doc = fitz.open(INPUT_PDF)

  # 1) Build TOC items by scanning the document
  items = build_toc_from_scan(doc)

  # 2) Decide insertion point
  # We want to insert TOC after page 2 (Cover + Impresszum).
  # Page indices 0 and 1 are Cover/Impresszum.
  # So we insert at index 2.
  insertion_index = 2

  # 3) Render TOC to temp file to determine its length
  # First pass: final_page_1based is just a placeholder (orig page)
  for it in items:
    it.final_page_1based = it.orig_page_1based

  rect = doc[0].rect
  page_size = (rect.width, rect.height)
  
  render_toc_pdf(items, TOC_TMP_PDF, page_size)
  
  with fitz.open(TOC_TMP_PDF) as t:
      toc_pages = t.page_count

  # 4) Compute final page numbers
  # If we insert `toc_pages` at `insertion_index`, then:
  # Any page that was at index `i` >= `insertion_index` will move to `i + toc_pages`.
  # Orig pages are 1-based. `insertion_index` 2 means pages 1, 2 stay. Page 3 becomes 3+toc_pages.
  # So if orig_page_1based > insertion_index, add toc_pages.
  
  for it in items:
    if it.orig_page_1based > insertion_index:
      it.final_page_1based = it.orig_page_1based + toc_pages
    else:
      it.final_page_1based = it.orig_page_1based

  # 5) Re-render TOC with correct numbers
  # (If the page numbers growing causes TOC to grow by another page, we might need a loop, 
  # but usually TOC is small enough or stable enough).
  render_toc_pdf(items, TOC_TMP_PDF, page_size)
  
  # Check if page count changed (rare edge case)
  with fitz.open(TOC_TMP_PDF) as t:
      toc_pages2 = t.page_count
      
  if toc_pages2 != toc_pages:
      toc_pages = toc_pages2
      for it in items:
        if it.orig_page_1based > insertion_index:
          it.final_page_1based = it.orig_page_1based + toc_pages
        else:
          it.final_page_1based = it.orig_page_1based
      render_toc_pdf(items, TOC_TMP_PDF, page_size)

  # 6) Merge: insert TOC into original
  toc_doc = fitz.open(TOC_TMP_PDF)
  out = fitz.open()
  
  # Insert pages before insertion point
  out.insert_pdf(doc, from_page=0, to_page=insertion_index-1)
  
  # Insert TOC
  out.insert_pdf(toc_doc)
  
  # Insert pages after insertion point
  out.insert_pdf(doc, from_page=insertion_index, to_page=doc.page_count-1)

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