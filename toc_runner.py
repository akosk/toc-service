# toc_runner.py
import os
import tempfile
import fitz

from toc_core import (
  extract_toc_titles,
  find_title_occurrence_ordered,
  render_toc_pdf,
)

def add_toc_to_pdf(input_pdf: str, output_pdf: str):
  """
  Reads input_pdf, appends a styled TOC at the end,
  writes output_pdf.
  """

  doc = fitz.open(input_pdf)

  # extract TOC items
  toc_titles = extract_toc_titles(doc)
  items = find_title_occurrence_ordered(doc, toc_titles, start_search_page_index=2)

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
