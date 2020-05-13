from time import sleep
import os
import json
import asyncio
import re
from typing import Tuple, Optional, List, Dict, Any

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
    prices: Optional[Dict[str, Any]]

    def format_color_string(cost):
        c_map = {"R": "🔴", "U": "🔵", "G": "🟢", "B": "⚫", "W": "⚪", "C": "⟡"}
        curly_brace_regex = r"\{(.*?)\}"

        formatted_string = "**"
        arr = re.findall(curly_brace_regex, cost)

        for cost_symbol in arr:
            if cost_symbol in c_map:
                formatted_string += c_map[cost_symbol]
            else:
                formatted_string += f"({cost_symbol})"

        return formatted_string + "**"

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

        embed.set_image(url=card.normal_image)

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

        color_identity = MagicCard.format_color_identity(raw_card["color_identity"])
        normal_image = raw_card["image_uris"]["normal"]
        prices = raw_card["prices"]

        splat = {
            **raw_card,
            **{
                "color_identity": color_identity,
                "normal_image": normal_image,
                "prices": prices,
            },
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
