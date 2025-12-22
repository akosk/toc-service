# test_local.py
import fitz
import tempfile
import os

from toc_core import (
  build_toc_from_scan,
  render_toc_pdf,
)

INPUT_PDF = r"C:\dev\vers.pdf"
OUTPUT_PDF = r"C:\dev\vers_with_toc_test.pdf"

doc = fitz.open(INPUT_PDF)

items = build_toc_from_scan(doc)

# TOC appended → page numbers unchanged
for it in items:
  it.final_page_1based = it.orig_page_1based

rect = doc[0].rect
page_size = (rect.width, rect.height)

with tempfile.TemporaryDirectory() as td:
  toc_pdf = os.path.join(td, "toc.pdf")
  render_toc_pdf(items, toc_pdf, page_size)

  out = fitz.open()
  out.insert_pdf(doc)
  out.insert_pdf(fitz.open(toc_pdf))
  out.save(OUTPUT_PDF)

print("OK:", OUTPUT_PDF)
