# 🏥 Medical Document Anonymizer

A tool for anonymizing and simplifying medical documents.  
Supports text extraction, translation, sensitive data removal, and generation of user-friendly PDF reports.

---

## ✨ Features

### 📂 Multi-format Extraction
- Extract text from:
  - **PDF**
  - **DOCX**
  - **Images** (JPG, PNG) via OCR

### 🌐 Automatic Language Detection
- Detects document language  
- Supported: **English, German, Russian**

### 🔄 Translation
- Translate documents between:
  - **English ↔ German ↔ Russian**
- Powered by state-of-the-art neural models

### 🔒 Anonymization
Removes personal and sensitive data using a combination of:
- **Microsoft Presidio** (PII detection)
- **XLM-RoBERTa NER** (Named Entity Recognition)
- **Custom Regex Patterns**

### 📑 PDF Generation with Highlights
- Generates a new PDF  
- All redacted data is **highlighted** for clarity

### 🧾 Medical Explanation (ChatGPT)
- Optional plain-language explanation of medical findings  
- Powered by **ChatGPT**

### 🌐 Web Interface
- User-friendly **Flask web app**  
- Upload files and view results directly in your browser

---

## ⚙️ How It Works

1. **Upload a File**  
   Upload your medical document via the web interface.

2. **Text Extraction**  
   - OCR for images/PDF  
   - Direct parsing for DOCX

3. **Language Detection & Translation**  
   - Detects language  
   - Translates to **English** for processing (if needed)

4. **Anonymization**  
   - Detects and replaces personal data (names, dates, emails, phone numbers, IDs, etc.) with `[REDACTED]`.

5. **Cleaning & Logging**  
   - Every cleaning step is **logged** for transparency.

6. **PDF Generation**  
   - Creates a new PDF with all **redacted sections highlighted**.

7. **Medical Explanation (optional)**  
   - Get a plain-language summary of medical findings.

---

## 🛠️ Technologies Used

- **Python 3**
- **Flask** — web framework
- **pytesseract** — OCR ([Tesseract](https://sourceforge.net/projects/tesseract-ocr.mirror/))
- **transformers** — HuggingFace MarianMT, XLM-RoBERTa
- **Microsoft Presidio** — PII detection
- **reportlab** — PDF generation
- **langdetect** — language detection
- **OpenAI GPT** — medical explanations

---
