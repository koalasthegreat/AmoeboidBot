from pydantic import BaseModel
from typing import Tuple, Optional, Dict, Any
from discord import Embed, Color
from datetime import date

import re


class MagicCard(BaseModel):
    name: str
    color_identity: Tuple[Any, ...]
    normal_image_url: str
    normal_image_bytes: bytes
    oracle_text: Optional[str]
    flavor_text: Optional[str]
    scryfall_uri: str
    color_string: Optional[str]
    type_line: Optional[str]
    power: Optional[str]
    toughness: Optional[str]
    loyalty: Optional[str]
    prices: Optional[Dict[str, Any]]
    set: Optional[str]
    set_name: Optional[str]

    def format_color_string(cost):
        c_map = {"R": "🔴", "U": "🔵", "G": "🟢", "B": "🟣", "W": "⚪", "C": "⟡"}
        curly_brace_regex = r"\{(.*?)\}"

        formatted_string = ""
        arr = re.findall(curly_brace_regex, cost)

        for cost_symbol in arr:
            if cost_symbol in c_map:
                formatted_string += c_map[cost_symbol]
            else:
                formatted_string += f"({cost_symbol})"

        return f"**{formatted_string}**" if formatted_string != "" else ""

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
        embed = Embed(type="rich")
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
        embed.colour = Color.from_rgb(r, g, b)

        if card.color_string is not None and card.color_string != "":
            embed.add_field(name="Cost:", value=card.color_string)

        if card.type_line is not None:
            embed.add_field(name="Type:", value=card.type_line)

        if card.loyalty is not None:
            embed.add_field(name="Loyalty:", value=card.loyalty)

        if card.power is not None:
            embed.add_field(name="Stats:", value=f"{card.power}/{card.toughness}")

        if card.set is not None and card.set_name is not None:
            set_string = f"[{card.set.upper()}] {card.set_name}"
            embed.add_field(name="Set:", value=set_string)

        if card.prices is not None:
            price_string = MagicCard.format_prices(card.prices)
            embed.add_field(name="Prices:", value=price_string)

        return embed


class MagicCardRuling(BaseModel):
    published_at: date
    source: str
    comment: str
