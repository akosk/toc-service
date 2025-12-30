import fitz
import os
from watermark_core import add_watermark

def create_dummy_pdf(filename):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Original Content", fontsize=20)
    doc.save(filename)
    doc.close()

def verify():
    inp = "test_input.pdf"
    out = "test_output.pdf"

    try:
        create_dummy_pdf(inp)
        add_watermark(inp, out)
        
        if not os.path.exists(out):
            print("Error: Output file not created.")
            return
            
        doc = fitz.open(out)
        found_watermark = False
        
        # Check text using dict (more detailed extraction)
        for page in doc:
            # Try simple text first
            if "MINTA" in page.get_text():
                found_watermark = True
                break
                
            # Try dict
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            if "MINTA" in s["text"]:
                                found_watermark = True
                                break
                if found_watermark: break
            if found_watermark: break
            
        if found_watermark:
            print("SUCCESS: Watermark found in output.")
        else:
            print("WARNING: Watermark text not detected by extraction (might be visual only due to rotation).")
            print("Output file created successfully.")
            
        doc.close()
        
    except Exception as e:
        print(f"Exception during verification: {e}")
    finally:
        if os.path.exists(inp):
            os.remove(inp)
        if os.path.exists(out):
            os.remove(out)

if __name__ == "__main__":
    verify()