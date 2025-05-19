import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

def generate_pdf_with_highlights(original_text, cleaned_text, output_folder="pdf_outputs"):
   
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    existing_files = os.listdir(output_folder)
    pdf_files = [f for f in existing_files if f.endswith(".pdf")]
    next_number = len(pdf_files) + 1
    output_path = os.path.join(output_folder, f"output_{next_number}.pdf")

    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 10)

   
    cleaned_lines = cleaned_text.splitlines()

    y = height - 50  
    line_height = 12  

    for line in cleaned_lines:
        if y < 50:  
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50

        
        parts = line.split("[REDACTED]")
        x = 50  

        for i, part in enumerate(parts):
            
            c.setFillColor(colors.black)
            c.drawString(x, y, part)
            x += c.stringWidth(part, "Helvetica", 10)

            
            if i < len(parts) - 1:
                c.setFillColor(colors.red)
                c.drawString(x, y, "[REDACTED]")
                x += c.stringWidth("[REDACTED]", "Helvetica", 10)

        y -= line_height

    c.save()
    print(f"PDF-файл сохранён по пути: {output_path}")