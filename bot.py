from time import sleep
import datetime
import ast
import os
import json
import asyncio
import re
from typing import Tuple, Optional, List, Dict, Any
from io import BytesIO, StringIO

import requests
import sqlite3
import discord
from inflection import camelize
from discord.ext import commands
from dotenv import load_dotenv
from pydantic import BaseModel, validator
from PIL import Image


load_dotenv()
DISCORD_TOKEN = os.getenv("AMOEBOID_DISCORD_TOKEN")
TCGPLAYER_TOKEN = os.getenv("AMOEBOID_TCGPLAYER_TOKEN")
DEFAULT_PREFIX = os.getenv("AMOEBOID_DEFAULT_PREFIX", default="a!")
DEFAULT_WRAPPING = os.getenv("AMOEBOID_DEFAULT_WRAPPING", default="[[*]]")
DB_NAME = os.getenv("AMOEBOID_DB_NAME", default="bot.db")
REFRESH_INTERVAL = int(os.getenv("ABOEBOID_REFRESH_INTERVAL", default=24))


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


def get_prefix(client, message):
    if not message.guild:
        return DEFAULT_PREFIX
    return bot_settings.get_prefix(message.guild.id)


class MagicCard(BaseModel):
    id: int
    artist: Optional[str]
    ascii_name: Optional[str]
    availability: Optional[List[str]]
    borderColor: Optional[str]
    card_kingdom_foil_id: Optional[str]
    card_kingdom_id: Optional[str]
    color_identity: Optional[List[str]]
    color_indicator: Optional[List[str]]
    colors: Optional[List[str]]
    converted_mana_cost: Optional[float]
    duel_deck: Optional[str]
    edhrec_rank: Optional[int]
    face_converted_mana_cost: Optional[float]
    face_name: Optional[str]
    flavor_name: Optional[str]
    flavor_text: Optional[str]
    frame_effects: Optional[List[str]]
    frame_version: Optional[str]
    hand: Optional[str]
    has_alternative_deck_limit: Optional[bool]
    has_content_warning: Optional[bool]
    has_foil: Optional[bool]
    has_non_foil: Optional[bool]
    is_alternative: Optional[bool]
    is_full_art: Optional[bool]
    is_online_only: Optional[bool]
    is_oversized: Optional[bool]
    is_promo: Optional[bool]
    is_reprOptional: Optional[bool]
    is_reserved: Optional[bool]
    is_starter: Optional[bool]
    is_story_spotlight: Optional[bool]
    is_textless: Optional[bool]
    is_timeshifted: Optional[bool]
    keywords: Optional[List[str]]
    layout: Optional[str]
    leadership_skills: Optional[Dict[str, str]]
    life: Optional[str]
    loyalty: Optional[str]
    mana_cost: Optional[str]
    mcm_id: Optional[str]
    mcm_meta_id: Optional[str]
    mtg_arena_id: Optional[str]
    mtgjson_v4_id: Optional[str]
    mtgo_foil_id: Optional[str]
    mtgo_id: Optional[str]
    multiverse_id: Optional[str]
    name: Optional[str]
    number: Optional[str]
    original_release_date: Optional[datetime.date]
    original_text: Optional[str]
    original_type: Optional[str]
    other_face_ids: Optional[List[str]]
    power: Optional[str]
    printings: Optional[List[str]]
    promo_types: Optional[List[str]]
    purchase_urls: Optional[Dict[str, str]]
    rarity: Optional[str]
    scryfall_id: Optional[str]
    scryfall_illustration_id: Optional[str]
    scryfall_oracle_id: Optional[str]
    set_code: Optional[str]
    side: Optional[str]
    subtypes: Optional[List[str]]
    supertypes: Optional[List[str]]
    tcgplayer_product_id: Optional[str]
    text: Optional[str]
    toughness: Optional[str]
    types: Optional[List[str]]
    uuid: str
    variations: Optional[List[str]]
    watermark: Optional[str]

    class Config:
        def camel_case(string):
            return camelize(string, uppercase_first_letter=False)

        alias_generator = camel_case
        allow_population_by_field_name = True

    @validator('availability', 'color_identity', 'color_indicator', 'colors', 'frame_effects', 'keywords', 'other_face_ids', 'printings',
    'promo_types', 'subtypes', 'supertypes', 'types', 'variations', pre=True)
    def parse_list_string(cls, val):
        if val is not None:
            if "," in val:
                return val.split(",")
            return [val]
        return None

    @validator('leadership_skills', 'purchase_urls', pre=True)
    def parse_dicts(cls, val):
        if val is not None:
            return ast.literal_eval(val)
        return None


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
        embed = discord.Embed(type="rich")
        embed.title = card.name

        prefix = ""

        embed.description = ""

        if card.text is not None:
            embed.description += card.text

        if embed.description != "":
            prefix = "\n\n"

        if card.flavor_text is not None:
            embed.description += f"{prefix}*{card.flavor_text}*"

        if embed.description != "":
            embed.description += f"\n\n[View on Scryfall]({card.scryfall_id})"

        r, g, b = MagicCard.format_color_identity(card.color_identity)
        embed.colour = discord.Color.from_rgb(r, g, b)

        if card.colors is not None:
            embed.add_field(name="Cost:", value=MagicCard.format_color_string(card.mana_cost))

        if card.types is not None:
            embed.add_field(name="Type:", value=" ".join(card.types))

        if card.loyalty is not None:
            embed.add_field(name="Loyalty:", value=card.loyalty)

        if card.power is not None:
            embed.add_field(name="Stats:", value=f"{card.power}/{card.toughness}")

        image_url = scryfall_api.get_image_url(card.scryfall_id)

        if image_url is not None:
            embed.set_image(url=image_url)

        # if card.prices is not None:
        #     price_string = MagicCard.format_prices(card.prices)
        #     embed.add_field(name="Prices:", value=price_string)

        return embed


class MagicCardRuling(BaseModel):
    published_at: datetime.date
    source: str
    comment: str


class BotSettings:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings
            (server_id text UNIQUE, prefix text, wrapping text)    
        """
        )
        self.conn.commit()

    def set_prefix(self, server_id, prefix):
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO settings
            (server_id, prefix, wrapping)
            VALUES(?, ?, ?)
        """,
            (server_id, DEFAULT_PREFIX, DEFAULT_WRAPPING),
        )

        self.cursor.execute(
            """
            UPDATE settings
            SET prefix=?
            WHERE server_id=?
        """,
            (prefix, server_id),
        )

        self.conn.commit()

    def set_wrapping(self, server_id, wrapping):
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO settings
            (server_id, prefix, wrapping)
            VALUES(?, ?, ?)
        """,
            (server_id, DEFAULT_PREFIX, DEFAULT_WRAPPING),
        )

        self.cursor.execute(
            """
            UPDATE settings
            SET wrapping=?
            WHERE server_id=?
        """,
            (wrapping, server_id),
        )

        self.conn.commit()

    def get_prefix(self, server_id):
        self.cursor.execute(
            "SELECT prefix FROM settings WHERE server_id=?", (server_id,)
        )
        result = self.cursor.fetchone()

        if result is not None:
            return result[0]
        else:
            return DEFAULT_PREFIX

    def get_wrapping(self, server_id):
        self.cursor.execute(
            "SELECT wrapping FROM settings WHERE server_id=?", (server_id,)
        )
        result = self.cursor.fetchone()

        if result is not None:
            return result[0]
        else:
            return DEFAULT_WRAPPING


class ScryfallAPI:
    def __init__(self):
        self.base_uri = "https://api.scryfall.com"

    # deprecated
    def get_cards(self, queries):
        cards = []

        for query in queries:
            payload = {"fuzzy": query["card_name"]}

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
                image = img_to_bytearray(stitch_images_horz(images, buf_horz=10))
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
    
    def get_image(self, scryfall_card_id):
        pass

    def get_image_url(self, scryfall_card_id):
        payload = {"format": "image", "version": "normal"}

        image_request = requests.get(f"{self.base_uri}/cards/{scryfall_card_id}", params=payload)

        if image_request.status_code == 404:
            return None

        return image_request.url

class TCGPlayerAPI:
    def __init__(self):
        self.base_uri = "https://api.tcgplayer.com"

    def get_prices(self, product_id):
        prices_request = requests.get(f"{self.base_uri}")


class CardDB:
    def __init__(self):
        self.conn = sqlite3.connect("AllPrintings.sqlite")
        self.conn.enable_load_extension(True)
        self.conn.row_factory = sqlite3.Row
        self.conn.load_extension('./spellfix')
        self.cursor = self.conn.cursor()

        self.init_virtual_table()


    def init_virtual_table(self):
        self.cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search USING spellfix1")
        self.cursor.execute("INSERT OR IGNORE INTO search(word) SELECT name FROM cards")

    def get_cards(self, queries):
        cards = []

        for query in queries:
            name = query["card_name"]

            if query.get("params") is None:
                carddb.cursor.execute(
                    """
                    SELECT word FROM search WHERE word MATCH ?
                """,
                (name,),
                )

                guess = carddb.cursor.fetchone()['word']

                carddb.cursor.execute(
                    """
                    SELECT * FROM cards WHERE name=?
                """,
                (guess,),
                )
                cards.append(MagicCard(**carddb.cursor.fetchone()))

            # else:
            #     carddb.

        return cards



bot_settings = BotSettings()
scryfall_api = ScryfallAPI()
carddb = CardDB()
bot = commands.Bot(command_prefix=get_prefix)



@bot.command(
    name="prefix",
    brief="Change/view the bot's prefix",
    description="""
Changes/views the bot's prefix for the server being run in.
Only usable by server administrators.    
""",
)
@commands.has_permissions(administrator=True)
async def _change_prefix(ctx, prefix=None):
    if prefix is None:
        prefix = bot_settings.get_prefix(ctx.message.guild.id)
        await ctx.send(f"The bot's prefix for this server is currently `{prefix}`.")

    else:
        bot_settings.set_prefix(ctx.message.guild.id, prefix)
        await ctx.send(f"Bot prefix changed to `{prefix}`.")


@bot.command(
    name="wrapping",
    aliases=["wrap", "wrapper"],
    brief="Change or view the bot's wrapping",
    description="""
Changes/shows the card wrapping detection for the server 
being run in. Only usable by server administrators.
""",
)
@commands.has_permissions(administrator=True)
async def _change_wrapping(ctx, wrapping=None):
    if wrapping is None:
        wrapping = bot_settings.get_wrapping(ctx.message.guild.id)
        await ctx.send(f"The bot's wrapping for this server is currently `{wrapping}`.")

    else:
        regex = r"([^\s\*]+\*[^\s\*]+)"

        if re.match(regex, wrapping):
            bot_settings.set_wrapping(ctx.message.guild.id, wrapping)
            await ctx.send(f"Bot wrapping changed to `{wrapping}`.")

        else:
            await ctx.send(
                "Bot wrapping is not valid. Wrap a \* in characters, like this: `[[*]]`"
            )

# TODO: Refactor to use DB
@bot.command(
    name="rulings",
    aliases=["rule", "ruling"],
    brief="Shows rulings for the given card",
    description="""
Looks up and displays the rulings for the given card. Will sort
them into rulings from both WOTC and Scryfall.
""",
)
async def _get_rulings(ctx, *card_name):
    if len(card_name) < 1:
        raise commands.MissingRequiredArgument(_get_rulings.params["card_name"])

    card_name = " ".join(card_name)

    card = scryfall_api.get_cards([{"card_name": card_name}])
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

# TODO: refactor to use local db to get illustration from api
@bot.command(
    name="art",
    aliases=["artwork"],
    brief="Shows artwork for a card from a given set (if it exists)",
    description="""
Looks up card artwork from the specified set, and sends the cropped art
along with more info about the work, if it exists.
""",
)
async def _get_art(ctx, set, *card_name):
    if len(card_name) < 1:
        raise commands.MissingRequiredArgument(_get_art.params["card_name"])

    card_name = " ".join(card_name)
    set_id = set.lower()

    card = scryfall_api.get_cards(
        [
            {
                "card_name": card_name,
                "set": set_id,
            }
        ]
    )

    if len(card) > 0:
        name = card[0][0]["name"]

        if card[0][0].get("image_uris").get("art_crop"):
            art_uri = card[0][0]["image_uris"]["art_crop"]
            artist_name = card[0][0]["artist"]
            flavor_text = card[0][0].get("flavor_text")

            embed = discord.Embed(type="rich")
            embed.title = name + f" ({set_id.upper()})"
            embed.set_image(url=art_uri)
            embed.description = f"*{flavor_text}*" if flavor_text else None
            embed.set_footer(text=f"{artist_name} — ™ and © Wizards of the Coast")

            await ctx.send(embed=embed)

        else:
            await ctx.send(f"No art found for card with name `{name}`.")
    else:
        await ctx.send(f"Art for card `{card_name}` from set `{set_id.upper()}` not found.")


@bot.event
async def on_ready():
    print("Bot is online")


@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    wrapping = None

    if not message.guild:
        if DEFAULT_PREFIX in message.content:
            await bot.process_commands(message)
            return
        wrapping = DEFAULT_WRAPPING

    else:
        if bot_settings.get_prefix(message.guild.id) in message.content:
            await bot.process_commands(message)
            return
        wrapping = bot_settings.get_wrapping(message.guild.id)

    left_split, right_split = wrapping.split("*")

    if left_split and right_split not in message.content:
        return

    regex = rf"{re.escape(left_split)}(.*?){re.escape(right_split)}"
    raw_queries = re.findall(regex, message.content)

    if len(raw_queries) > 10:
        await message.channel.send("Please request 10 or less cards at a time.")
        return

    queries = []

    for query in raw_queries:
        query = query.split(";")

        if len(query) == 1:
            query = {"card_name": query[0]}
            queries.append(query)
        else:
            params = query[1:]
            query = {
                "card_name": query[0],
                "params": [],
            }

            try:
                for param in params:
                    param = param.split("=")
                    query["params"].append({param[0].strip(" "): param[1].strip(" ")})
                queries.append(query)
            except:
                await message.channel.send("Invalid formatting of parameters.")
                return

    cards = carddb.get_cards(queries)

    if len(cards) == 0:
        await message.channel.send("Could not find any cards.")

    elif len(cards) == 1:
        card = cards[0]

        embed = MagicCard.generate_embed(card)

        await message.channel.send(embed=embed)

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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f"You do not have permission to run the command `{ctx.command}`."
        )
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"`{ctx.command}` is not a valid command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument `{error.param}`.")
    else:
        raise error


bot.run(DISCORD_TOKEN)
