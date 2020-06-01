from time import sleep
import os
import json
import asyncio
import re
from typing import Tuple, Optional, List, Dict, Any
from io import BytesIO

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
        embed.description += card.oracle_text

        if embed.description != "":
            prefix = "\n\n"
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

        embed.set_image(url=card.normal_image_url)

        return embed


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

                print(raw_card)

                image_request = requests.get(raw_card["image_uris"]["normal"])
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


scryfall_api = ScryfallAPI()


@bot.event
async def on_ready():
    print("Bot is online")


@bot.event
async def on_message(message):
    if ("[" not in message.content) or (message.author.bot):
        return

    count = 0

    square_bracket_regex = r"\[(.*?)\]"
    card_names = re.findall(square_bracket_regex, message.content)
    raw_cards = scryfall_api.get_cards(card_names)
    cards = []

    for raw_card, image in raw_cards:
        color_identity = MagicCard.format_color_identity(raw_card["color_identity"])
        normal_image_url = raw_card["image_uris"]["normal"]
        prices = raw_card["prices"]

        splat = {
            **raw_card,
            **{
                "color_identity": color_identity,
                "normal_image_url": normal_image_url,
                "normal_image_bytes": image,
                "prices": prices,
            },
        }
        card = MagicCard(**splat)

        cards.append(card)

    if len(cards) == 1:
        card = cards[0]

        embed = MagicCard.generate_embed(cards[0])
        await message.channel.send(embed=embed)

    elif len(cards) <= 10 and len(cards) > 1:
        images = []

        for card in cards:
            stream = BytesIO(card.normal_image_bytes)
            image = Image.open(stream)
            images.append(image)

        buf = 20
        parsed_image = Image.new(
            "RGB",
            (
                (len(images) + 1) * buf + sum(image.width for image in images),
                2 * buf + images[0].height,
            ),
            color=(255, 255, 255),
        )

        width_offset = buf

        test = None

        for image in images:
            parsed_image.paste(image, (width_offset, buf))
            width_offset += image.width + buf

        parsed_image_bytes = BytesIO()
        parsed_image.save(parsed_image_bytes, format="jpeg")

        parsed_image_bytes.seek(0)

        file = discord.File(parsed_image_bytes, filename="cards.jpg")
        await message.channel.send(
            f"Retrieved {len(cards)} cards. Call a single card for more details.",
            file=file,
        )
    elif len(cards) > 10:
        await message.channel.send("Please request 10 or less cards at a time.")


bot.run(TOKEN)
