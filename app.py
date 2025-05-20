from flask import Flask, render_template, request
from extractors import extract_text_from_pdf, extract_text_from_image, extract_text_from_docx
from cleaners import process_text_in_chunks
from langdetect import detect
from openai_utils import generate_explanation
from translator import (
    translate_text_de_to_en,
    translate_text_ru_to_en,
    translate_text_en_to_de,
    translate_text_en_to_ru
)
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PDF_OUTPUT_FOLDER'] = 'static/pdf_outputs'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PDF_OUTPUT_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process_file():
    file = request.files['file']
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        if file.filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        elif file.filename.endswith('.docx'):
            extracted_text = extract_text_from_docx(file_path)
        elif file.filename.endswith(('.jpg', '.jpeg', '.png')):
            extracted_text = extract_text_from_image(file_path)
        else:
            return "Unsupported file type", 400

        detected_language = detect(extracted_text)
        print(f"Detected language: {detected_language}")

        if detected_language == "de":
            print("Document is in German. Translating to English...")
            extracted_text = translate_text_de_to_en(extracted_text)
            print("Translated text:")
            print(extracted_text)
        elif detected_language == "ru":
            print("Document is in Russian. Translating to English...")
            extracted_text = translate_text_ru_to_en(extracted_text)
            print("Translated text:")
            print(extracted_text)

        cleaned_text, logs = process_text_in_chunks(extracted_text)

        if detected_language == "de":
            print("Translating cleaned text back to German...")
            cleaned_text = translate_text_en_to_de(cleaned_text)
            print("Cleaned text in German:")
            print(cleaned_text)
        elif detected_language == "ru":
            print("Translating cleaned text back to Russian...")
            cleaned_text = translate_text_en_to_ru(cleaned_text)
            print("Cleaned text in Russian:")
            print(cleaned_text)

        print(f"Extracted text: {extracted_text[:100]}")
        print(f"Cleaned text: {cleaned_text[:100]}")

        return render_template(
            'result.html',
            extracted_text=extracted_text,
            logs=logs,
            cleaned_text=cleaned_text
        )


@app.route('/generate_explanation', methods=['POST'])
def generate_explanation_route():
    cleaned_text = request.form['cleaned_text']
    explanation = generate_explanation(cleaned_text)

    return render_template(
        'result.html',
        explanation=explanation,
        cleaned_text=cleaned_text,
        extracted_text=request.form.get('extracted_text', ''),
        logs=request.form.getlist('logs'),
        pdf_filename=request.form.get('pdf_filename', '')
    )


if __name__ == '__main__':
    app.run(debug=True)
