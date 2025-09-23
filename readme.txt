Medical Document Anonymizer
.

Features
Multi-format Extraction:
Extracts text from PDFs, DOCX, and images (JPG, PNG, ) using OCR and text parsing.

Automatic Language Detection:
Detects the language of the document (supports English, German, Russian).

Translation:
Seamlessly translates documents between English, German, and Russian using state-of-the-art neural models.

Anonymization:
Removes personal and sensitive information using a combination of:

Microsoft Presidio (PII detection)
XLM-RoBERTa NER (Named Entity Recognition)
Custom regex patterns
PDF Generation with Highlights:
Generates a new PDF with all redacted information clearly highlighted.

Medical Explanation (ChatGPT):
Optionally sends cleaned text to ChatGPT for a plain-language explanation of medical findings.

Web Interface:
User-friendly Flask web app for uploading files and viewing results.

How It Works
Upload a File:
Upload your medical document via the web interface.

Text Extraction:
The system extracts text using OCR (for images/PDFs) or direct parsing (for DOCX).

Language Detection & Translation:
The language is detected and, if needed, the text is translated to English for processing.

Anonymization:
All personal data (names, dates, emails, phone numbers, IDs, etc.) is detected and replaced with [REDACTED].

Cleaning & Logging:
The cleaning process is logged for transparency.

PDF Generation:
A new PDF is generated with all redacted sections highlighted.

Medical Explanation
Users can request a plain-language explanation of the medical findings via ChatGPT.

Technologies Used
Python 3
Flask (web framework)
pytesseract (OCR) https://sourceforge.net/projects/tesseract-ocr.mirror/
transformers (HuggingFace MarianMT, XLM-RoBERTa)
Microsoft Presidio (PII detection)
reportlab (PDF generation)
langdetect (language detection)
OpenAI GPT (medical explanations)
