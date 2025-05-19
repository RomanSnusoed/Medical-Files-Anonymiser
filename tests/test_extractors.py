
"""
import os
from extractors import extract_text_from_pdf, extract_text_from_docx, extract_text_from_image

def test_extract_text_from_pdf():
    test_pdf = "test.pdf"
    if not os.path.exists(test_pdf):
        print("test.pdf not found, skipping test_extract_text_from_pdf")
        return
    text = extract_text_from_pdf(test_pdf)
    assert isinstance(text, str)
    print("PDF extraction OK")

def test_extract_text_from_docx():
    test_docx = "test.docx"
    if not os.path.exists(test_docx):
        print("test.docx not found, skipping test_extract_text_from_docx")
        return
    text = extract_text_from_docx(test_docx)
    assert isinstance(text, str)
    print("DOCX extraction OK")

def test_extract_text_from_image():
    test_img = "test.jpg"
    if not os.path.exists(test_img):
        print("test.jpg not found, skipping test_extract_text_from_image")
        return
    text = extract_text_from_image(test_img)
    assert isinstance(text, str)
    print("Image extraction OK")

if __name__ == "__main__":
    test_extract_text_from_pdf()
    test_extract_text_from_docx()
    test_extract_text_from_image()
    print("All tests finished.")

    """