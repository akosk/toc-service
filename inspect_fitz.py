import fitz
doc = fitz.open()
page = doc.new_page()
mat = fitz.Matrix(45)
try:
    # insert_text(point, text, ... morph=(point, matrix))
    # Note: the point argument to insert_text might be ignored or used as default?
    # Let's pass a dummy point for the first arg.
    page.insert_text((0, 0), "MORPH", morph=(fitz.Point(100, 100), mat))
    print("morph worked")
except Exception as e:
    print(f"morph failed: {e}")

# Save and check content
doc.save("test_morph.pdf")
doc2 = fitz.open("test_morph.pdf")
print("Text content:", doc2[0].get_text())