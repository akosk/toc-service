
import fitz
import sys

def inspect(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return

    print(f"Page count: {doc.page_count}")
    
    # Inspect pages 0 to 15 (or less if fewer pages)
    for i in range(min(16, doc.page_count)):
        page = doc[i]
        blocks = page.get_text("dict")["blocks"]
        print(f"--- Page {i} ---")
        
        # Get first text block
        text_blocks = [b for b in blocks if b["type"] == 0]
        if not text_blocks:
            print("(No text)")
            continue
            
        first_block = text_blocks[0]
        if not first_block["lines"]:
            print("(Empty block)")
            continue
            
        first_line = first_block["lines"][0]
        if not first_line["spans"]:
            print("(Empty line)")
            continue
            
        # Check the first span of the first line
        span = first_line["spans"][0]
        text = span["text"]
        font = span["font"]
        size = span["size"]
        color = span["color"]
        flags = span["flags"]
        
        print(f"First line text: '{text}'")
        print(f"Font: {font}, Size: {size:.2f}, Flags: {flags}")
        
        # Check if there are more spans in the first line (mixed formatting)
        full_line_text = "".join(s["text"] for s in first_line["spans"])
        print(f"Full first line: '{full_line_text}'")

        # Also print number of lines on page to help identify chapter pages
        line_count = sum(len(b["lines"]) for b in text_blocks)
        print(f"Total lines on page: {line_count}")

if __name__ == "__main__":
    inspect("c:\\dev\\vers.pdf")
