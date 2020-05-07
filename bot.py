from time import sleep
import os
import json
import asyncio
import re
from typing import Tuple, Optional, List, Any

import requests
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pydantic import BaseModel, validator

load_dotenv()
TOKEN = os.getenv("TOKEN")
PREFIX = os.getenv("PREFIX", default="a!")

bot = commands.Bot(command_prefix=PREFIX)


class MagicCard(BaseModel):
    name: str
    color_identity: Tuple[Any, ...]
    normal_image: str
    oracle_text: Optional[str]
    flavor_text: Optional[str]
    scryfall_uri: str
    mana_cost: Optional[str]
    type_line: Optional[str]
    power: Optional[str]
    toughness: Optional[str]
    loyalty: Optional[str]

    def get_cost_string(cost):
        formatted_string = "**"
        arr = cost.split("{")

        c_map = {
            "R": "🔴",
            "U": "🔵",
            "G": "🟢",
            "B": "⚫",
            "W": "⚪",
            "C": "⟡"
        }

        for char in arr:
            if len(char) != 0:
                c = char[0]

                if c in c_map:
                    formatted_string += c_map[c]
                else:
                    formatted_string += f"({c})"

        return formatted_string + "**"

    def get_color_identity(color):
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

    def generate_embed(card):
        embed = discord.Embed(type="rich")
        embed.title = card.name

        if card.loyalty is not None:
            embed.add_field(name="Loyalty:", value=card.loyalty)

        if card.power is not None:
            embed.add_field(name="Stats:", value=f"{card.power}/{card.toughness}")

        if card.type_line is not None:
            embed.add_field(name="Type:", value=card.type_line)

        embed.description = ""

        prefix = ""
        if embed.description != "":
            prefix = "\n\n"
        embed.description += f"{prefix}*{card.flavor_text}*"

        if embed.description != "":
            embed.description += f"\n\n[View on Scryfall]({card.scryfall_uri})"

        if card.mana_cost is not None and card.mana_cost != "":
            embed.add_field(
                name="Cost:", value=MagicCard.get_cost_string(card.mana_cost)
            )

        embed.description += card.oracle_text
        embed.set_image(url=card.normal_image)

        r, g, b = card.color_identity
        embed.colour = discord.Color.from_rgb(r, g, b)

        embed.title = card.name
        return embed


class ScryfallAPI:
    def __init__(self):
        self.cache = (
            {}
        )  # TODO make cache sqlite instead of python world so it maintains between starts / no eat ram
        self.base_uri = "https://api.scryfall.com"

    def get_card(self, name):
        if name in self.cache:
            return self.cache[name]
        else:
            payload = {"fuzzy": name}
            r = requests.get(f"{self.base_uri}/cards/named", params=payload)
            sleep(0.25)  # todo better rate limiting
            json = r.json()
            self.cache[name] = json
            return json


@bot.event
async def on_ready():
    print("Bot is online")


scryfall_api = ScryfallAPI()


@bot.event
async def on_message(message):
    if "[" not in message.content and message.author.bot:
        return

    count = 0

    square_bracket_regex = r"\[(.*?)\]"
    card_names = re.findall(square_bracket_regex, message.content)
    cards = []

    for name in card_names:
        raw_card = scryfall_api.get_card(name)

        color_identity = MagicCard.get_color_identity(raw_card["color_identity"])
        normal_image = raw_card["image_uris"]["normal"]

        splat = {
            **raw_card,
            **{"color_identity": color_identity, "normal_image": normal_image},
        }
        card = MagicCard(**splat)

        cards.append(card)

    for card in cards:
        if count >= 5:
            await message.channel.send(
                "To prevent spam, only 5 cards can be processed at one time. Please make another query."
            )
            return

        count += 1
        embed = MagicCard.generate_embed(card)
        await message.channel.send(embed=embed)
        await asyncio.sleep(1)


bot.run(TOKEN)
