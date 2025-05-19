from PIL import Image, ImageEnhance
import pytesseract
import re
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image_path):
    """
    Preprocesses the image for better OCR results.
    """
    img = Image.open(image_path)
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)  
    img = img.convert('L')  # Convert to grayscale

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(4)  # Increase contrast
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.5)  # Increase brightness

    return img

def correct_image_orientation(image):
    """
    Detects and corrects the orientation of the image using Tesseract OSD.
    """
    try:
        osd = pytesseract.image_to_osd(image)
        rotation_angle = int(re.search(r"Rotate: (\d+)", osd).group(1))
        if rotation_angle != 0:
            print(f"Rotating image by {rotation_angle} degrees")
            image = image.rotate(-rotation_angle, expand=True)
    except Exception as e:
        print(f"Error detecting orientation: {e}")
    return image