from extractors import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
)
from cleaners import process_text_in_chunks
from openai_utils import generate_explanation
from translator import (
    translate_text_de_to_en,
    translate_text_en_to_de,
    translate_text_ru_to_en,
    translate_text_en_to_ru,
)
from langdetect import detect
from pdf_generator import generate_pdf_with_highlights

mapping = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "image": extract_text_from_image,
}

if __name__ == "__main__":
    file_path = (
        r"C:\Users\38066\Dr-Adem Dropbox\Team General\AI\Reports\Dummy Text files\001fakede.docx"
    )
    extracted_text = ""

    # Extract text depending on file type
    if file_path.endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        extracted_text = extract_text_from_docx(file_path)
    elif file_path.endswith((".jpg", ".jpeg", ".png", ".tiff")):
        extracted_text = extract_text_from_image(file_path)
    else:
        print("Unsupported file type.")
        extracted_text = ""

    if extracted_text:
        print("Extracted text:")
        print(extracted_text)

        # Detect language
        detected_language = detect(extracted_text)
        print(f"Detected language: {detected_language}")

        # Translate to English if needed
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

        # Clean the text
        cleaned_text, logs = process_text_in_chunks(extracted_text, chunk_size=300)
        print("\nCleaned text:")
        print(cleaned_text)

        # Translate cleaned text back to original language if needed
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

        # Generate PDF with highlights
        generate_pdf_with_highlights(
            extracted_text, cleaned_text, output_folder="output_folder"
        )

        # Ask user if they want to send text to ChatGPT for explanation
        user_input = input(
            "Send text to ChatGPT for explanation? (yes/no): "
        ).strip().lower()
        if user_input in ["yes", "y", "ja", "да"]:
            explanation = generate_explanation(cleaned_text)
            print("\nExplanation:")
            print(explanation)
        else:
            print("Request to ChatGPT cancelled.")

        # Ask user if they want to show cleaning logs
        user_input = input(
            "Show cleaning logs? (yes/no): "
        ).strip().lower()
        if user_input in ["yes", "y", "ja", "да"]:
            print("\nLogs:")
            for log in logs:
                print(log)
        else:
            print("Cleaning logs not displayed.")
