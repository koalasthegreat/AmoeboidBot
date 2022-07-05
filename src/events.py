from io import BytesIO
import os
import re
from nextcord.ext import commands
from PIL import Image

from api import scryfall_api
from botsettings import bot_settings
from formatting import format_color_identity, format_color_string, generate_embed, process_raw_cards
from images import (
    bytes_to_discfile,
    img_to_bytearray,
    stitch_images_horz,
    stitch_images_vert,
)
from models import MagicCard

DEFAULT_WRAPPING = os.getenv("DEFAULT_WRAPPING", default="[[*]]")


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or message.author.bot:
            return

        wrapping = None

        if not message.guild:
            wrapping = DEFAULT_WRAPPING

        else:
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
                        query["params"].append(
                            {param[0].strip(" "): param[1].strip(" ")}
                        )
                    queries.append(query)
                except:
                    await message.channel.send("Invalid formatting of parameters.")
                    return

        raw_cards = scryfall_api.get_cards(queries)
        cards = process_raw_cards(raw_cards)

        if len(cards) == 0:
            await message.channel.send("Could not find any cards.")

        elif len(cards) == 1:
            card = cards[0]

            embed = generate_embed(card)

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

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
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
