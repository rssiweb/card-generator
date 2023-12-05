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

TEMPLATE_URL = "https://res.cloudinary.com/hs4stt5kg/image/upload/v1690876629/ID%20Card/ID_Card_FINAL_php_V3.jpg"
USERS_FILE = "users.csv"

QR_POSITION = (700, 1405)  # (X, Y) - Adjust the values as needed
QR_SIZE = 500
FONT_SIZE_BIG = 65
FONT_SIZE_MEDIUM = 60
FONT_SIZE_SMALL = 55


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
    if person.role == "Student":
        content = f"https://login.rssi.in/rssi-student/verification.php?get_id={person.userid}"
    else:
        content = (
            f"https://login.rssi.in/rssi-member/verification.php?get_id={person.userid}"
        )
    return _get_barcode_for(content, size=size)


def _get_barcode_for(content, size):
    res = requests.get(
        f"https://chart.googleapis.com/chart?chs={size}x{size}&cht=qr&chl={content}"
    )
    return Image.open(io.BytesIO(res.content))


def generate_cards(persons):
    font_path = "Ubuntu-M.ttf"
    font = ImageFont.truetype(font_path, FONT_SIZE_BIG)
    img = open_image_from_url(TEMPLATE_URL)
    width, _ = img.size
    card_files = []
    for person in persons:
        dp = person.image and open_image_from_url(person.image)

        tmp_img = copy.copy(img)
        draw = ImageDraw.Draw(tmp_img)

        text_width, _ = draw.textsize(person.name, font=font)
        text_x = (width - text_width) / 2
        draw.text((text_x, 1155), person.name, (0, 0, 0), font=font)

        font = ImageFont.truetype(font_path, FONT_SIZE_MEDIUM)
        text_width, _ = draw.textsize(person.userid, font=font)
        text_x = (width - text_width) / 2
        draw.text((text_x, 1249), person.userid, (0, 0, 0), font=font)

        if dp:
            # h - 348 w - 300
            dp = dp.convert("RGB")
            dp = dp.resize((350, 470), Image.ANTIALIAS)
            x_off = (width - dp.size[0]) // 2
            tmp_img.paste(dp, (x_off, 650))
        else:
            logger.info(f"{person.name} - image not loaded")

        try:
            barcode_img = get_barcode_image(person, size=QR_SIZE)
        except Exception:
            logging.exception(f"{person.name} - barcode not loaded")
        else:
            tmp_img.paste(barcode_img, QR_POSITION)

            font = ImageFont.truetype(font_path, FONT_SIZE_SMALL)

            role = person.role if person.role else (" " * 20)
            text_width, _ = draw.textsize(role, font=font)
            text_x = (width - text_width) / 2
            draw.text((text_x, 1349), role, (0, 0, 0), font=font)

        card_filename = "card_{}.jpg".format(person.name)
        card_filepath = os.path.join("cards", card_filename)
        tmp_img.save(card_filepath, quality=95)
        card_files.append(card_filepath)
    return card_files


if __name__ == "__main__":
    users = read_users_from_file(USERS_FILE)
    generate_cards(users)