# toc_runner.py
import os
import tempfile
import fitz

from toc_core import (
  build_toc_from_scan,
  render_toc_pdf,
)

def add_toc_to_pdf(input_pdf: str, output_pdf: str):
  """
  Reads input_pdf, appends a styled TOC at the end,
  writes output_pdf.
  """

  doc = fitz.open(input_pdf)

  # extract TOC items by scanning
  items = build_toc_from_scan(doc)

  # TOC appended → page numbers unchanged
  for it in items:
    it.final_page_1based = it.orig_page_1based


  # match original page size exactly
  rect = doc[0].rect
  page_size = (rect.width, rect.height)

  with tempfile.TemporaryDirectory() as td:
    toc_pdf = os.path.join(td, "toc.pdf")

    render_toc_pdf(items, toc_pdf, page_size)

    toc_doc = fitz.open(toc_pdf)
    out = fitz.open()
    out.insert_pdf(doc)
    out.insert_pdf(toc_doc)
    out.save(output_pdf)

    toc_doc.close()
    out.close()

  doc.close()
