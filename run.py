import logging
import requests
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import copy
import io
import os
import csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

TEMPLATE_URL = "https://res.cloudinary.com/hs4stt5kg/image/upload/v1703182962/ID%20Card/back_5535174-2.jpg"
USERS_FILE = "users.csv"

# Assuming you want the QR code below the image with some vertical padding
y_off_qr = 820  # Adjust the Y coordinate as needed
FONT_SIZE_BIG = 65
FONT_SIZE_MEDIUM = 45
FONT_SIZE_SMALL = 40  # using

class COLUMNS:
    USER_ID = "Student_ID"
    ROLE = "Role"
    NAME = "Student Name"
    IMAGE = "Photo URL"

class Person:
    def __init__(self, name, userid, image, role):
        self.image = image and image.strip()
        self.name = name and name.strip().title()
        self.userid = userid and userid.strip()
        self.role = role and role.strip()

def open_image_from_url(url):
    try:
        res = requests.get(url)
        res.raise_for_status()  # Check if the request was successful
    except Exception as ex:
        logger.error(str(ex))
    else:
        try:
            image = Image.open(io.BytesIO(res.content))
        except Exception as ex:
            logger.error(f"url: {str(ex)}")
        else:
            return image

def read_users_from_file(filename):
    persons = []
    with open(filename, "r") as fh:
        reader = csv.DictReader(fh)
        for user in reader:
            persons.append(
                Person(
                    user.get(COLUMNS.NAME),
                    user.get(COLUMNS.USER_ID),
                    user.get(COLUMNS.IMAGE),
                    user.get(COLUMNS.ROLE),
                )
            )
    return persons

def get_barcode_image(person, size):
    try:
        if person.role == "Student":
            content = f"https://login.rssi.in/rssi-student/verification.php?get_id={person.userid}"
        else:
            content = f"https://login.rssi.in/rssi-member/verification.php?get_id={person.userid}"

        res = requests.get(
            f"https://api.qrserver.com/v1/create-qr-code/?data={content}&size={size}x{size}"
        )
        res.raise_for_status()  # Check if the request was successful

        return Image.open(io.BytesIO(res.content))
    except Exception as ex:
        logging.exception(f"{person.name} - barcode not loaded: {str(ex)}")
        return None

def generate_cards(persons):
    font_path = "Ubuntu-Medium.ttf"
    font_path_text = "Nunito-Regular.ttf"
    img = open_image_from_url(TEMPLATE_URL)
    width, _ = img.size
    card_files = []

    for person in persons:
        dp = person.image and open_image_from_url(person.image)

        tmp_img = copy.copy(img)
        draw = ImageDraw.Draw(tmp_img)

        if dp:
            # h - 348 w - 300
            dp = dp.convert("RGB")
            dp = dp.resize((350, 470), resample=Image.LANCZOS)
            x_off = (width - dp.size[0]) // 2
            tmp_img.paste(dp, (x_off, 150))
        else:
            logger.info(f"{person.name} - image not loaded")

        try:
            barcode_img = get_barcode_image(person, size=300)
            if barcode_img:
                barcode_img = barcode_img.convert("RGB")
                x_off_qr = (width - barcode_img.size[0]) // 2
                tmp_img.paste(barcode_img, (x_off_qr, y_off_qr))

                font = ImageFont.truetype(font_path, FONT_SIZE_MEDIUM)

                text_bbox = draw.textbbox((0, 0), person.name, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (width - text_width) / 2
                draw.text((text_x, 630), person.name, (0, 0, 0), font=font)

                font = ImageFont.truetype(font_path, FONT_SIZE_SMALL)
                text_bbox = draw.textbbox((0, 0), person.userid, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (width - text_width) / 2
                draw.text((text_x, 700), person.userid, (0, 0, 0), font=font)   

                role = person.role if person.role else (" " * 20)
                text_bbox = draw.textbbox((0, 0), role, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_x = (width - text_width) / 2
                draw.text((text_x, 750), role, (0, 0, 0), font=font)          

        except Exception:
            logging.exception(f"{person.name} - barcode not loaded")

        # Add hardcoded text horizontally with a 90-degree rotation
        hardcoded_text = "rssi.in"
        font_hardcoded = ImageFont.truetype(font_path_text, 100)

        # Create a transparent image with the same size as the main content
        transparent_img = Image.new("RGBA", tmp_img.size, (0, 0, 0, 0))

        # Draw the rotated hardcoded text on the transparent image
        rotated_text_draw = ImageDraw.Draw(transparent_img)
        rotated_text_draw.text((20, 20), hardcoded_text, (0, 0, 0), font=font_hardcoded)

        # Rotate the image by 90 degrees
        rotated_text_img = transparent_img.rotate(90, expand=True)

        # Calculate the position to paste the rotated text onto the main image
        x_hardcoded, y_hardcoded = 0, -500  # Adjust the position as needed

        # Paste the rotated text onto the main image only for the hardcoded text
        tmp_img.paste(rotated_text_img, (x_hardcoded, y_hardcoded), rotated_text_img)

        card_filename = f"card_{person.name}.jpg"
        card_filepath = os.path.join("cards", card_filename)
        tmp_img.save(card_filepath, quality=95)
        card_files.append(card_filepath)
    return card_files

if __name__ == "__main__":
    users = read_users_from_file(USERS_FILE)
    generate_cards(users)
