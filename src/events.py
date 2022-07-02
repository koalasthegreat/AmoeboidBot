from io import BytesIO
import os
import re
from nextcord.ext import commands
from api import ScryfallAPI
from PIL import Image

from botsettings import bot_settings
from formatting import format_color_identity, format_color_string, generate_embed
from images import (
    bytes_to_discfile,
    img_to_bytearray,
    stitch_images_horz,
    stitch_images_vert,
)
from models import MagicCard

DEFAULT_WRAPPING = os.getenv("DEFAULT_WRAPPING", default="[[*]]")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", default="a!")


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
            if DEFAULT_PREFIX in message.content:
                await self.bot.process_commands(message)
                return
            wrapping = DEFAULT_WRAPPING

        else:
            if bot_settings.get_prefix(message.guild.id) in message.content:
                await self.bot.process_commands(message)
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
                        query["params"].append(
                            {param[0].strip(" "): param[1].strip(" ")}
                        )
                    queries.append(query)
                except:
                    await message.channel.send("Invalid formatting of parameters.")
                    return

        raw_cards = ScryfallAPI.get_cards(queries)
        cards = []

        for raw_card, image in raw_cards:
            splat = raw_card

            if raw_card["layout"] == "split":
                left = raw_card["card_faces"][0]
                right = raw_card["card_faces"][1]

                color_string = [left.get("mana_cost"), right.get("mana_cost")]
                color_string = [
                    item for item in color_string if item is not None and item != ""
                ]
                color_string = [format_color_string(cost) for cost in color_string]
                color_string = " // ".join(color_string)

                oracle_text = [left.get("oracle_text"), right.get("oracle_text")]
                oracle_text = [item for item in oracle_text if item is not None]
                oracle_text = "\n----\n".join(oracle_text)
                if oracle_text == "":
                    oracle_text = None

                flavor_text = [left.get("flavor_text"), right.get("flavor_text")]
                flavor_text = [item for item in flavor_text if item is not None]
                flavor_text = "\n----\n".join(flavor_text)
                if flavor_text == "":
                    flavor_text = None

                color_identity = format_color_identity(raw_card["color_identity"])
                normal_image_url = raw_card["image_uris"]["normal"]

                splat.update(
                    {
                        "oracle_text": oracle_text,
                        "flavor_text": flavor_text,
                        "color_string": color_string,
                        "normal_image_url": normal_image_url,
                        "normal_image_bytes": image,
                        "color_identity": color_identity,
                    }
                )
            elif raw_card["layout"] == "transform":
                front_face = raw_card["card_faces"][0]

                normal_image_url = front_face["image_uris"]["normal"]
                oracle_text = front_face.get("oracle_text")
                flavor_text = front_face.get("flavor_text")
                color_string = format_color_string(front_face.get("mana_cost"))
                color_identity = format_color_identity(raw_card["color_identity"])
                power = front_face.get("power")
                toughness = front_face.get("toughness")
                loyalty = front_face.get("loyalty")

                splat.update(
                    {
                        "normal_image_url": normal_image_url,
                        "normal_image_bytes": image,
                        "oracle_text": oracle_text,
                        "flavor_text": flavor_text,
                        "color_string": color_string,
                        "power": power,
                        "toughness": toughness,
                        "loyalty": loyalty,
                        "color_identity": color_identity,
                    }
                )
            elif raw_card["layout"] == "modal_dfc":
                front_face = raw_card["card_faces"][0]
                back_face = raw_card["card_faces"][1]

                normal_image_url = front_face["image_uris"]["normal"]

                color_string = [front_face.get("mana_cost"), back_face.get("mana_cost")]
                color_string = [
                    item for item in color_string if item is not None and item != ""
                ]
                color_string = [format_color_string(cost) for cost in color_string]
                color_string = " // ".join(color_string)

                oracle_text = [
                    front_face.get("oracle_text"),
                    back_face.get("oracle_text"),
                ]
                oracle_text = [item for item in oracle_text if item is not None]
                oracle_text = "\n----\n".join(oracle_text)
                if oracle_text == "":
                    oracle_text = None

                flavor_text = [
                    front_face.get("flavor_text"),
                    back_face.get("flavor_text"),
                ]
                flavor_text = [item for item in flavor_text if item is not None]
                flavor_text = "\n----\n".join(flavor_text)
                if flavor_text == "":
                    flavor_text = None

                color_identity = format_color_identity(raw_card["color_identity"])

                splat.update(
                    {
                        "normal_image_url": normal_image_url,
                        "normal_image_bytes": image,
                        "oracle_text": oracle_text,
                        "flavor_text": flavor_text,
                        "color_string": color_string,
                        "color_identity": color_identity,
                    }
                )

            else:
                normal_image_url = raw_card["image_uris"]["normal"]
                color_string = format_color_string(raw_card.get("mana_cost"))
                color_identity = format_color_identity(raw_card["color_identity"])

                splat.update(
                    {
                        "normal_image_url": normal_image_url,
                        "normal_image_bytes": image,
                        "color_identity": color_identity,
                        "color_string": color_string,
                    }
                )

            prices = raw_card["prices"]

            splat.update(
                {
                    "prices": prices,
                }
            )

            card = MagicCard(**splat)

            cards.append(card)

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
