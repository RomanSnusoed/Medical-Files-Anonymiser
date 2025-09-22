from cleaners import load_ignore_words
from cleaners import clean_and_remove_personal_info
from extractors import extract_text_from_pdf, extract_text_from_image, extract_text_from_docx
from openai_utils import generate_explanation
from utils import correct_image_orientation, preprocess_image
from unittest.mock import patch, MagicMock


def test_ignorewords():
    ignorewords = load_ignore_words("ignorewords.txt")
    assert isinstance(ignorewords, set)
    assert len(ignorewords) > 0  

def test_ignorewords2():
    ignorewords = load_ignore_words("ignorewords.txt")
    assert "Alanine" in ignorewords
    assert "Alison" not in ignorewords
    assert "Calium" in ignorewords
    


def test_presidio():
    text = "My name is Roman and I live in New York. My email is roman@example.com"

    FakeResult = type("FakeResult", (), {})
    fake_person = FakeResult()
    fake_person.start = 11
    fake_person.end = 16
    fake_person.entity_type = "PERSON"

    fake_email = FakeResult()
    fake_email.start = 44
    fake_email.end = 60
    fake_email.entity_type = "EMAIL"

    with patch("cleaners.analyzer") as mock_analyzer:
        mock_analyzer.analyze.return_value = [fake_person, fake_email]
        cleaned_text, logs = clean_and_remove_personal_info(text)
        assert "Roman" not in cleaned_text
        assert "roman@example.com" not in cleaned_text
        assert "[REDACTED]" in cleaned_text



def test_roberta_mocking():
    text = "My name is Roman."
    fake_entity = {'start': 11, 'end': 15, 'entity_group': 'PERSON'}
    with patch("cleaners.ner_pipeline", return_value=[fake_entity]):
        cleaned, logs = clean_and_remove_personal_info(text)
        assert "Roman" not in cleaned
        assert "[REDACTED]" in cleaned      




def test_language_detection_mocking():
    text = "Mein Name ist Herr Muller.Ich liebe die Schokolade."
    with patch("cleaners.detect", return_value="de") as mock_detect, \
         patch("cleaners.analyzer") as mock_analyzer:
        mock_analyzer.analyze.return_value = []
        cleaned, logs = clean_and_remove_personal_info(text)
        mock_detect.assert_called_once_with(text)
        


def test_regex_email_removal():
    text = "Contact: roman@dr-adem.com"
    with patch("cleaners.analyzer") as mock_analyzer, \
         patch("cleaners.ner_pipeline", return_value=[]):
        mock_analyzer.analyze.return_value = []
        cleaned, logs = clean_and_remove_personal_info(text)
        assert "roman@dr-adem.com" not in cleaned
        assert "[REDACTED]" in cleaned        
        


def test_extract_from_image():
    with patch("extractors.ensure_tesseract_cmd") as mock_ensure, \
        patch("extractors.preprocess_image") as mock_preprocess, \
        patch("extractors.pytesseract.image_to_string", return_value="mocked_text"):
        mock_preprocess.return_value = MagicMock()
        text = extract_text_from_image("fake.img")
        assert text == "mocked_text"
        mock_ensure.assert_called_once()



def test_extract_from_pdf():
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "PDF text"
    mock_pdf.__len__.return_value = 1
    mock_pdf.__getitem__.return_value = mock_page
    with patch("extractors.fitz.open", return_value=mock_pdf):
        text = extract_text_from_pdf("fake.pdf")
        assert "PDF text" in text        


def test_extract_text_from_docx():
    mock_doc = MagicMock()
    mock_doc.paragraphs = [MagicMock(text="Hello"), MagicMock(text="World")]
    with patch("extractors.docx.Document", return_value=mock_doc):
        text = extract_text_from_docx("fake.docx")
        assert "Hello" in text and "World" in text



def test_generate_explanation():
    fake_response = {
        "choices": [
            {"message": {"content": "Explanation text"}}
        ]
    }
    with patch("openai.ChatCompletion.create", return_value=fake_response) as mock_create:
        result = generate_explanation("Cleaned medical text")
        assert result == "Explanation text"
        mock_create.assert_called_once()        



def test_preprocess_image_mock():
    fake_img = MagicMock()
    fake_img.width = 50
    fake_img.height = 50
    fake_img.resize.return_value = fake_img
    fake_img.convert.return_value = fake_img

    with patch("utils.Image.open", return_value=fake_img):
        with patch("utils.ImageEnhance.Contrast") as mock_contrast, \
             patch("utils.ImageEnhance.Brightness") as mock_brightness:
            mock_contrast.return_value.enhance.return_value = fake_img
            mock_brightness.return_value.enhance.return_value = fake_img
            img = preprocess_image("fake.img")
            assert img == fake_img       




def test_extract_text_from_image_not_found():
    with patch("extractors.ensure_tesseract_cmd"), \
        patch("utils.Image.open", side_effect=FileNotFoundError):
        text = extract_text_from_image("no_such_file.jpg")
        assert text == ""



def test_presidio_error_handling():
    text = "My name is John."
    with patch("cleaners.analyzer") as mock_analyzer:
        mock_analyzer.analyze.side_effect = Exception("Presidio fail")
        cleaned, logs = clean_and_remove_personal_info(text)
        assert "Presidio error" in " ".join(logs)        