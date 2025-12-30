import fitz
import os

def add_watermark(input_pdf: str, output_pdf: str, text: str = "MINTA"):
    doc = fitz.open(input_pdf)
    
    font_path = os.path.join("fonts", "EBGaramond-Regular.ttf")
    has_custom_font = os.path.exists(font_path)

    fontsize = 60
    color = (0.5, 0.5, 0.5) # Gray
    
    for page in doc:
        fontname = "helv"
        
        if has_custom_font:
            # Register font for the page
            # page.insert_font returns the resource ID (int), but we need the name we assigned
            page.insert_font(fontfile=font_path, fontname="garamond")
            fontname = "garamond"
            
        # Calculate text width to center it
        if has_custom_font:
            font = fitz.Font(fontfile=font_path)
        else:
            font = fitz.Font(fontname)
            
        text_len = font.text_length(text, fontsize=fontsize)
        
        # Calculate centered position
        x = (page.rect.width - text_len) / 2
        y = page.rect.height / 2
        
        page.insert_text(
            (x, y),
            text,
            fontsize=fontsize,
            fontname=fontname, 
            color=color,
            fill_opacity=0.3
        )
        
    doc.save(output_pdf)