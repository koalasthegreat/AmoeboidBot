from time import sleep
import os
import json
import asyncio
import re
from typing import Tuple, Optional, List, Dict, Any
from io import BytesIO, StringIO
from datetime import date

import requests
import sqlite3
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pydantic import BaseModel, validator
from PIL import Image


load_dotenv()
TOKEN = os.getenv("TOKEN")
PREFIX = os.getenv("PREFIX", default="a!")

bot = commands.Bot(command_prefix=PREFIX)


def bytes_to_discfile(byte_arr, filename):
    iobytes = BytesIO(byte_arr)
    iobytes.seek(0)
    return discord.File(iobytes, filename=filename)


def img_to_bytearray(img):
    byte_arr = BytesIO()
    img.save(byte_arr, format="PNG")
    return byte_arr.getvalue()


def stitch_images_horz(images, buf_horz=0, buf_vert=0, bgcolor=(255, 255, 255)):
    new_img_size = (
        sum([img.width for img in images]) + buf_horz * (len(images) + 1),
        max([img.height for img in images]) + buf_vert * 2,
    )
    new_img = Image.new("RGB", new_img_size, color=bgcolor)
    for idx, paste_img in enumerate(images):
        paste_img_loc = (
            sum([img.width for img in images[:idx]]) + buf_horz * (idx + 1),
            buf_vert,
        )
        new_img.paste(paste_img, paste_img_loc)
    return new_img


def stitch_images_vert(images, buf_horz=0, buf_vert=0, bgcolor=(255, 255, 255)):
    new_img_size = (
        max([img.width for img in images]) + buf_horz * 2,
        sum([img.height for img in images]) + buf_vert * (len(images) + 1),
    )
    new_img = Image.new("RGB", new_img_size, color=bgcolor)
    for idx, paste_img in enumerate(images):
        paste_img_loc = (
            buf_horz,
            sum([img.height for img in images[:idx]]) + buf_vert * (idx + 1),
        )
        new_img.paste(paste_img, paste_img_loc)
    return new_img


class MagicCard(BaseModel):
    name: str
    color_identity: Tuple[Any, ...]
    normal_image_url: str
    normal_image_bytes: bytes
    oracle_text: Optional[str]
    flavor_text: Optional[str]
    scryfall_uri: str
    mana_cost: Optional[str]
    type_line: Optional[str]
    power: Optional[str]
    toughness: Optional[str]
    loyalty: Optional[str]
    prices: Optional[Dict[str, Any]]

    def format_color_string(cost):
        c_map = {"R": "🔴", "U": "🔵", "G": "🟢", "B": "⚫", "W": "⚪", "C": "⟡"}
        curly_brace_regex = r"\{(.*?)\}"

        formatted_string = ""
        arr = re.findall(curly_brace_regex, cost)

        for cost_symbol in arr:
            if cost_symbol in c_map:
                formatted_string += c_map[cost_symbol]
            else:
                formatted_string += f"({cost_symbol})"

        return f"**{formatted_string}**"

    def format_color_identity(color):
        color_map = {
            "R": (221, 46, 68),
            "U": (85, 172, 238),
            "G": (120, 177, 89),
            "B": (49, 55, 61),
            "W": (230, 231, 232),
            "C": (100, 101, 102),
        }

        if len(color) == 0:
            return (100, 101, 102)

        if len(color) == 1:
            color = color[0]
            if color in color_map:
                return color_map[color]

        else:
            return (207, 181, 59)

    def format_prices(prices):
        price_string = ""
        usd = prices.get("usd")
        usd_foil = prices.get("usd_foil")

        if usd:
            price_string += "Normal: " + (prices.get("usd") or "N/A") + " USD\n"
        else:
            price_string += "Normal: N/A\n"
        if usd_foil:
            price_string += "Foil: " + (prices.get("usd_foil") or "N/A") + " USD"
        else:
            price_string += "Foil: N/A"

        return price_string

    def generate_embed(card):
        embed = discord.Embed(type="rich")
        embed.title = card.name

        prefix = ""

        embed.description = ""

        if card.oracle_text is not None:
            embed.description += card.oracle_text

        if embed.description != "":
            prefix = "\n\n"

        if card.flavor_text is not None:
            embed.description += f"{prefix}*{card.flavor_text}*"

        if embed.description != "":
            embed.description += f"\n\n[View on Scryfall]({card.scryfall_uri})"

        r, g, b = card.color_identity
        embed.colour = discord.Color.from_rgb(r, g, b)

        if card.mana_cost is not None and card.mana_cost != "":
            embed.add_field(
                name="Cost:", value=MagicCard.format_color_string(card.mana_cost)
            )

        if card.type_line is not None:
            embed.add_field(name="Type:", value=card.type_line)

        if card.loyalty is not None:
            embed.add_field(name="Loyalty:", value=card.loyalty)

        if card.power is not None:
            embed.add_field(name="Stats:", value=f"{card.power}/{card.toughness}")

        if card.prices is not None:
            price_string = MagicCard.format_prices(card.prices)
            embed.add_field(name="Prices:", value=price_string)

        return embed


class MagicCardRuling(BaseModel):
    published_at: date
    source: str
    comment: str


class ScryfallAPI:
    def __init__(self):
        self.base_uri = "https://api.scryfall.com"

        self.conn = sqlite3.connect("cache.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cards
            (name text UNIQUE, raw_card text, image blob)
        """
        )
        self.conn.commit()

    def get_cards(self, names):
        cards = []

        for name in names:
            self.cursor.execute(
                """
                SELECT raw_card, image FROM cards WHERE name LIKE ?
            """,
                [name],
            )
            query_response = self.cursor.fetchone()

            if query_response is not None:
                cards.append([json.loads(query_response[0]), query_response[1]])
            else:
                payload = {"fuzzy": name}
                card_request = requests.get(
                    f"{self.base_uri}/cards/named", params=payload
                )
                sleep(0.25)  # TODO better rate limiting

                if card_request.status_code == 404:
                    print(f"Card with name {name} not found. Skipping")
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
                    image = img_to_bytearray(stitch_images_horz(images, buf_horz=10))
                else:
                    normal_image_url = raw_card["image_uris"]["normal"]
                    image_request = requests.get(normal_image_url)
                    sleep(0.25)
                    image = bytearray(image_request.content)

                self.cursor.execute(
                    """
                    INSERT OR IGNORE INTO cards VALUES (?,?,?)
                """,
                    [raw_card["name"], json.dumps(raw_card), image],
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


scryfall_api = ScryfallAPI()


@bot.command(
    name="rulings",
    brief="Shows rulings for the given card",
    description="""
Looks up and displays the rulings for the given card. Will sort
them into rulings from both WOTC and Scryfall.
""",
)
async def _get_rulings(ctx, *args):
    card_name = " ".join(args)

    card = scryfall_api.get_cards([card_name])
    sleep(0.25)  # TODO: better ratelimiting

    if len(card) > 0 and card[0][0].get("rulings_uri"):
        card_name = card[0][0]["name"]
        rulings = scryfall_api.get_rulings(card[0][0]["rulings_uri"])

        if len(rulings) == 0:
            await ctx.send(f"Could not find rulings for `{card_name}`.")
            return

        rulings = [ruling for ruling in rulings if ruling.source == "wotc"]

        embed = discord.Embed(type="rich")
        embed.title = "Rulings for " + card_name

        description = ""

        for ruling in rulings:
            description += (
                "**"
                + ruling.published_at.strftime("%m/%d/%Y")
                + "**: "
                + ruling.comment
                + "\n\n"
            )

        embed.description = description.strip()

        if len(description) > 2048:
            embed.description = (
                embed.description[:1900]
                + f"...\n\n[View Full Rulings on Scryfall]({card[0][0]['scryfall_uri']})"
            )

        await ctx.send(embed=embed)

    else:
        await ctx.send(f"Card with name `{card_name}` not found.")


@bot.event
async def on_ready():
    print("Bot is online")


@bot.event
async def on_message(message):
    if ("[" not in message.content) or (message.author.bot):
        await bot.process_commands(message)
        return

    count = 0

    square_bracket_regex = r"\[(.*?)\]"
    card_names = re.findall(square_bracket_regex, message.content)

    if len(card_names) > 10:
        await message.channel.send("Please request 10 or less cards at a time.")
        return

    raw_cards = scryfall_api.get_cards(card_names)
    cards = []

    for raw_card, image in raw_cards:
        prices = raw_card["prices"]
        color_identity = MagicCard.format_color_identity(raw_card["color_identity"])

        splat = raw_card

        if raw_card.get("card_faces") is not None:
            front_face = raw_card["card_faces"][0]

            normal_image_url = front_face["image_uris"]["normal"]
            oracle_text = front_face.get("oracle_text")
            flavor_text = front_face.get("flavor_text")
            colors = front_face.get("colors")
            mana_cost = front_face.get("mana_cost")
            power = front_face.get("power")
            toughness = front_face.get("toughness")
            loyalty = front_face.get("loyalty")

            splat.update(
                {
                    "normal_image_url": normal_image_url,
                    "normal_image_bytes": image,
                    "oracle_text": oracle_text,
                    "flavor_text": flavor_text,
                    "colors": colors,
                    "mana_cost": mana_cost,
                    "power": power,
                    "toughness": toughness,
                    "loyalty": loyalty,
                }
            )

        else:
            normal_image_url = raw_card["image_uris"]["normal"]
            splat.update(
                {
                    "normal_image_url": normal_image_url,
                    "normal_image_bytes": image,
                }
            )

        splat.update(
            {
                "prices": prices,
                "color_identity": color_identity,
            }
        )

        card = MagicCard(**splat)

        cards.append(card)

    if len(cards) == 0:
        await message.channel.send("Could not find any cards.")

    elif len(cards) == 1:
        card = cards[0]

        embed = MagicCard.generate_embed(card)

        img = bytes_to_discfile(card.normal_image_bytes, "card.jpg")
        embed.set_image(url="attachment://card.jpg")

        await message.channel.send(embed=embed, file=img)

    else:
        images = []

        for card in cards:
            stream = BytesIO(card.normal_image_bytes)
            image = Image.open(stream)
            images.append(image)

        # Note/cmdr0 - Should be able to use stitch_images with some business
        #   logic here; current math does not account for dual-faced cards
        # Note/koalasthegreat - Refactored to use the stitch_images functions,
        #   accounting for the width of dual card images still not implemented

        parsed_image = None

        if len(images) <= 5:
            parsed_image = stitch_images_horz(images, buf_horz=10, buf_vert=10)

        else:
            top = stitch_images_horz(images[:5], buf_horz=10, buf_vert=5)
            bottom = stitch_images_horz(images[5:], buf_horz=10, buf_vert=5)

            parsed_image = stitch_images_vert([top, bottom])

        parsed_image_bytes = img_to_bytearray(parsed_image)
        parsed_image_file = bytes_to_discfile(parsed_image_bytes, "cards.jpg")

        await message.channel.send(
            f"Retrieved {len(cards)} cards. Call a single card for more details.",
            file=parsed_image_file,
        )


bot.run(TOKEN)
