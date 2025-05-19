
from presidio_analyzer import AnalyzerEngine
from transformers import pipeline
import re
from langdetect import detect
from roberta import XlmRobertaNER
from concurrent.futures import ThreadPoolExecutor

# Load ignore words list

def load_ignore_words(file_path="ignorewords.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print(f"File {file_path} not found. Ignore words not loaded.")
        return set()

# Load ignore words
ignorewords = load_ignore_words()

# Initialize models
analyzer = AnalyzerEngine()
xlmr_recognizer = XlmRobertaNER()
ner_pipeline = pipeline("ner", model="Davlan/xlm-roberta-base-ner-hrl", grouped_entities=True)

def apply_replacements(text, replacements):
    """Apply replacements, checking for overlaps."""
    replacements.sort(key=lambda x: x[0], reverse=True)  # Sort descending
    for start, end, repl in replacements:
        text = text[:start] + repl + text[end:]
    return text

def is_valid_date_format(text):
    """Checks if the text matches a date format or contains age."""
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",  # dd/mm/yyyy or dd-mm-yyyy
        r"\b\d{4}-\d{2}-\d{2}\b",            # yyyy-mm-dd
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b",  # Month dd, yyyy
        r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December),? \d{4}\b",  # dd Month yyyy
        r"\b(?:Date of Birth|DOB|Report Date):?\s*\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December),? \d{4}\b",  # Date of Birth: dd Month yyyy
        r"\b(?:Date of Birth|DOB|Report Date):?\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"  # Date of Birth: dd/mm/yyyy
        r"\b\d{1,2}\s(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s\d{4}\b"
        r" \b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2}\)?"
    ]
    # Check if text matches date format
    if any(re.search(pattern, text) for pattern in date_patterns):
        return True

    # Additional check for age
    age_patterns = [
        r"\b\d{1,3}\s?(?:year|years|yr|yrs)\s?old\b",  # e.g., "29 years old", "29yr old"
        r"\b\d{1,3}\s?(?:year|years|yr|yrs)\b",        # e.g., "29 years", "29yr"
        r"\b\d{1,3}-?(?:year|years|yr|yrs)-?old\b"     # e.g., "29-year-old", "29yr-old"
    ]
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in age_patterns):
        return True

    return False

def clean_and_remove_personal_info(text):
    original_text = text
    logs = []

    presidio_logs = []
    roberta_logs = []
    regex_logs = []

    replacements = []  # Array of replacements: (start, end, "[REDACTED]")

    # --- Presidio ---
    # presidio_logs.append("found by Presidio")
    try:
        language = detect(original_text)
        presidio_results = analyzer.analyze(
            text=original_text,
            language=language,
            entities=["PERSON", "LOCATION", "EMAIL", "DATE_TIME"]
        )
        for result in presidio_results:
            pii = original_text[result.start:result.end]
            if result.entity_type == "DATE_TIME":
                # Check if entity matches date or age format
                if not is_valid_date_format(pii):
                    presidio_logs.append(f"Ignoring non-date entity: {pii}")
                    continue
            if pii in ignorewords:
                presidio_logs.append(f"Ignoring PII: {pii} (type: {result.entity_type})")
                continue
            presidio_logs.append(f"Removing PII: {pii} (type: {result.entity_type})")
            replacements.append((result.start, result.end, "[REDACTED]"))
    except Exception as e:
        presidio_logs.append(f"Presidio error: {e}")

    # --- XLM-R ---
    # roberta_logs.append("found by xlm-roberta...")
    try:
        entities = ner_pipeline(original_text)
        for ent in entities:
            word = original_text[ent['start']:ent['end']]
            if ent['entity_group'] == "DATE_TIME":
                # Check if entity matches date or age format
                if not is_valid_date_format(word):
                    roberta_logs.append(f"Ignoring non-date entity: {word}")
                    continue
            if word in ignorewords:
                roberta_logs.append(f"Ignoring entity: {word} (type: {ent['entity_group']})")
                continue
            roberta_logs.append(f"Removing entity: {word} (type: {ent['entity_group']})")
            replacements.append((ent['start'], ent['end'], "[REDACTED]"))
    except Exception as e:
        roberta_logs.append(f"NER error: {e}")

    # --- Regex ---
    # regex_logs.append("found by regular expressions...")

    def process_regex(pattern, label, original_text, regex_logs, replacements):
        """Processes regex synchronously."""
        matches = re.finditer(pattern, original_text)
        local_logs = []  # Local logs for current thread
        for match in matches:
            match_text = match.group()
            if match_text in ignorewords or match_text == "[REDACTED]":
                local_logs.append(f"Ignoring {label}: {match_text}")
                continue
            local_logs.append(f"Removing {label}: {match_text}")
            replacements.append((match.start(), match.end(), "[REDACTED]"))
        regex_logs.extend(local_logs)  # Add logs to main list after processing

    phone_pattern = r"\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{0,9}"
    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    patient_id_pattern = r"Patient ID:\s*[A-Z]{2}-\d{4}"
    patient_file_pattern = r"Patient File:\s*[A-Z]{2}-[A-Z]{3}-\d{5}"

    # Asynchronous regex processing
    with ThreadPoolExecutor() as executor:
        executor.submit(process_regex, phone_pattern, "phone number", original_text, regex_logs, replacements)
        executor.submit(process_regex, email_pattern, "email", original_text, regex_logs, replacements)
        executor.submit(process_regex, patient_id_pattern, "patient ID", original_text, regex_logs, replacements)
        executor.submit(process_regex, patient_file_pattern, "patient file", original_text, regex_logs, replacements)

    # --- Apply replacements ---
    cleaned_text = apply_replacements(original_text, replacements)

    logs.extend(presidio_logs)
    logs.extend(roberta_logs)
    logs.extend(regex_logs)

    return cleaned_text, logs

# rewrite in multiprocessing

def process_text_in_chunks(text, chunk_size=300):
    """Splits text into smaller chunks and processes them in parallel."""
    from concurrent.futures import ThreadPoolExecutor

    # Split text into chunks
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    cleaned_chunks = [None] * len(chunks)  # Preserve order
    all_logs = [None] * len(chunks)  # Preserve order

    def process_chunk(index, chunk):
        """Processes a single chunk of text."""
        cleaned_chunk, logs = clean_and_remove_personal_info(chunk)
        cleaned_chunks[index] = cleaned_chunk
        all_logs[index] = logs

    # Asynchronous chunk processing
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_chunk, i, chunk) for i, chunk in enumerate(chunks)]
        for future in futures:
            future.result()  # Wait for all threads to finish

    # Combine cleaned chunks
    cleaned_text = ''.join(cleaned_chunks)
    logs = [log for chunk_logs in all_logs for log in chunk_logs]  # Preserve log order
    return cleaned_text, logs


