import sqlite3
import requests


class ScryfallAPI:
    def __init__(self):
        self.base_uri = "https://api.scryfall.com"

        self.conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cards
            (name text UNIQUE, raw_card text, image blob, last_refreshed timestamp)
        """
        )
        self.conn.commit()

    def get_cards(self, queries):
        cards = []
        accepted_params = ["set"]

        for query in queries:
            query_response = None

            if not query.get("params"):
                self.cursor.execute(
                    """
                    SELECT raw_card, image, last_refreshed FROM cards WHERE name LIKE ?
                """,
                    [query["card_name"]],
                )
                query_response = self.cursor.fetchone()

            if query_response is not None:
                if (datetime.datetime.now() - query_response[2]) < datetime.timedelta(
                    hours=REFRESH_INTERVAL
                ):
                    cards.append([json.loads(query_response[0]), query_response[1]])
                    continue

            payload = {"fuzzy": query["card_name"]}
            if query.get("params"):
                for param in query["params"]:
                    for key in param:
                        if key in accepted_params:
                            payload[key] = param[key]

            card_request = requests.get(f"{self.base_uri}/cards/named", params=payload)
            sleep(0.25)  # TODO better rate limiting

            if card_request.status_code == 404:
                print(f"Card with name {query['card_name']} not found. Skipping")
                continue

            raw_card = card_request.json()

            normal_image_url = None
            if raw_card.get("image_uris") is None:
                images = []
                for face in raw_card["card_faces"]:
                    image_url = face["image_uris"]["normal"]
                    image_resp = requests.get(image_url)
                    face_image = Image.open(BytesIO(image_resp.content))
                    images.append(face_image)
                image = image_manip.img_to_bytearray(
                    image_manip.stitch_images_horz(images, buf_horz=10)
                )
            else:
                normal_image_url = raw_card["image_uris"]["normal"]
                image_request = requests.get(normal_image_url)
                sleep(0.25)
                image = bytearray(image_request.content)

            if not query.get("params"):
                self.cursor.execute(
                    """
                    INSERT OR REPLACE INTO cards VALUES (?,?,?,?)
                """,
                    [
                        raw_card["name"],
                        json.dumps(raw_card),
                        image,
                        datetime.datetime.now(),
                    ],
                )
                self.conn.commit()
            cards.append((raw_card, image))

        return cards

    def get_rulings(self, rulings_uri):
        ruling_request = requests.get(rulings_uri)

        if ruling_request.status_code == 200:
            raw_rulings = ruling_request.json()
            rulings = []

            for ruling in raw_rulings["data"]:
                rulings.append(MagicCardRuling(**ruling))

            return rulings

        else:
            return []
