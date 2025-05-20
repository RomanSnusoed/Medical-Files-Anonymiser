import fitz
import pytesseract
from PIL import Image
import docx
import io
import os
from utils import preprocess_image, correct_image_orientation

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_from_image(image_path):
    """
    Extracts text from an image file using OCR.
    """
    try:
        img = preprocess_image(image_path)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""


def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file. If no text is found, extracts text from images in the PDF.
    """
    text = ""
    try:
        pdf_document = fitz.open(pdf_path)
        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            page_text = page.get_text()
            if page_text.strip():
                text += page_text + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        pdf_document = None

    # If no text found, extract from images
    if pdf_document:
        print("Text not found in PDF, extracting images...")
        os.makedirs("processed_images", exist_ok=True)
        for page_number in range(len(pdf_document)):
            page = pdf_document[page_number]
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                image = correct_image_orientation(image)
                image_path = f"processed_images/page_{page_number + 1}_image_{img_index + 1}.jpg"
                image.save(image_path, "JPEG")
                print(f"Image saved as {image_path}")
                text += pytesseract.image_to_string(image) + "\n"
    return text


def extract_text_from_docx(docx_path):
    """
    Extracts text from a DOCX file.
    """
    try:
        doc = docx.Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from docx: {e}")
        return ""
        
