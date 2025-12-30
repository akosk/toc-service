from watermark_core import add_watermark

INPUT_PDF = r"C:\dev\vers.pdf"
OUTPUT_PDF = r"C:\dev\vers_with_watermark_test.pdf"

add_watermark(INPUT_PDF, OUTPUT_PDF, text="MINTA")

print("OK:", OUTPUT_PDF)
