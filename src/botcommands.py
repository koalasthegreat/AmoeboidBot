import re
from time import sleep
import nextcord
from nextcord.ext import commands

from botsettings import bot_settings
from api import scryfall_api


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
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

    @commands.command(
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
            await ctx.send(
                f"The bot's wrapping for this server is currently `{wrapping}`."
            )

        else:
            regex = r"([^\s\*]+\*[^\s\*]+)"

            if re.match(regex, wrapping):
                bot_settings.set_wrapping(ctx.message.guild.id, wrapping)
                await ctx.send(f"Bot wrapping changed to `{wrapping}`.")

            else:
                await ctx.send(
                    "Bot wrapping is not valid. Wrap a \* in characters, like this: `[[*]]`"
                )


class Rulings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
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
            raise commands.MissingRequiredArgument(card_name)

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

            embed = nextcord.Embed(type="rich")
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


class Artwork(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
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
            raise commands.MissingRequiredArgument(card_name)

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

                embed = nextcord.Embed(type="rich")
                embed.title = name + f" ({set_id.upper()})"
                embed.set_image(url=art_uri)
                embed.description = f"*{flavor_text}*" if flavor_text else None
                embed.set_footer(text=f"{artist_name} — ™ and © Wizards of the Coast")

                await ctx.send(embed=embed)

            else:
                await ctx.send(f"No art found for card with name `{name}`.")
        else:
            await ctx.send(
                f"Art for card `{card_name}` from set `{set_id.upper()}` not found."
            )
