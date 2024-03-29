import re
from time import sleep
from typing import Optional
import nextcord
from nextcord.ext import commands

from settings import bot_settings
from api import scryfall_api
from formatting import generate_embed, process_raw_cards
from images import bytes_to_discfile


class Cards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(
        name="card",
        description="Fetches a single card",
    )
    async def _get_card(
        self,
        interaction: nextcord.Interaction,
        name: str,
        set: Optional[str] = nextcord.SlashOption(required=False),
    ):
        await interaction.response.defer()

        raw_cards = scryfall_api.get_cards(
            [
                {
                    "card_name": name,
                    "params": [
                        {
                            "set": set,
                        }
                    ],
                }
            ]
        )

        cards = process_raw_cards(raw_cards)

        if len(cards) == 1:
            card = cards[0]

            embed = generate_embed(card)

            img = bytes_to_discfile(card.normal_image_bytes, "card.jpg")
            embed.set_image(url="attachment://card.jpg")

            await interaction.send(embed=embed, file=img)

        else:
            await interaction.send(f"No card found named `{name}` with those details")

    @_get_card.on_autocomplete("name")
    async def _card_name_autocomplete(self, interaction, name):
        if name and len(name) > 2:
            autocomplete = scryfall_api.get_autocomplete(name)

            await interaction.response.send_autocomplete(autocomplete.get("data"))
            return
        else:
            await interaction.response.send_autocomplete([])


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(
        name="wrapping",
        description="Change/view the bot's wrapping",
        dm_permission=False,
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def _change_wrapping(
        self,
        interaction: nextcord.Interaction,
        wrapping: Optional[str] = nextcord.SlashOption(required=False),
    ):
        await interaction.response.defer()

        if wrapping is None:
            wrapping = bot_settings.get_wrapping(interaction.guild_id)
            await interaction.send(
                f"The bot's wrapping for this server is currently `{wrapping}`.",
                ephemeral=True,
            )

        else:
            regex = r"([^\s\*]+\*[^\s\*]+)"

            if re.match(regex, wrapping):
                bot_settings.set_wrapping(interaction.guild_id, wrapping)
                await interaction.send(
                    f"Bot wrapping changed to `{wrapping}`.", ephemeral=True
                )

            else:
                await interaction.send(
                    "Bot wrapping is not valid. Wrap a \* in characters, like this: `[[*]]`",
                    ephemeral=True,
                )


class Rulings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(
        name="rulings",
        description="Show rulings for the given card",
    )
    async def _get_rulings(self, interaction: nextcord.Interaction, name: str):
        await interaction.response.defer()

        card = scryfall_api.get_cards([{"card_name": name}])
        sleep(0.25)  # TODO: better ratelimiting

        if len(card) > 0 and card[0][0].get("rulings_uri"):
            name = card[0][0]["name"]
            scryfall_uri = card[0][0].get("scryfall_uri")
            rulings = scryfall_api.get_rulings(card[0][0]["rulings_uri"])

            if len(rulings) == 0:
                await interaction.send(f"Could not find rulings for `{name}`.")
                return

            rulings = [ruling for ruling in rulings if ruling.source == "wotc"]

            embed = nextcord.Embed(type="rich")
            embed.title = "Rulings for " + name
            embed.url = scryfall_uri

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

            await interaction.send(embed=embed)

        else:
            await interaction.send(f"Card with name `{name}` not found.")

    @_get_rulings.on_autocomplete("name")
    async def _card_name_autocomplete(self, interaction, name):
        if name and len(name) > 2:
            autocomplete = scryfall_api.get_autocomplete(name)

            await interaction.response.send_autocomplete(autocomplete.get("data"))
            return
        else:
            await interaction.response.send_autocomplete([])


class Artwork(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(
        name="art",
        description="Look up card artwork",
    )
    async def _get_art(
        self,
        interaction: nextcord.Interaction,
        name: str,
        set: Optional[str] = nextcord.SlashOption(required=False),
    ):
        await interaction.response.defer()

        card = scryfall_api.get_cards(
            [
                {
                    "card_name": name,
                    "params": [
                        {
                            "set": set,
                        }
                    ],
                }
            ]
        )

        if len(card) > 0:
            name = card[0][0]["name"]

            if card[0][0].get("image_uris").get("art_crop"):
                art_uri = card[0][0]["image_uris"]["art_crop"]
                artist_name = card[0][0]["artist"]
                flavor_text = card[0][0].get("flavor_text")
                scryfall_uri = card[0][0].get("scryfall_uri")

                embed = nextcord.Embed(type="rich")
                embed.title = name + f" ({set.upper()})" if set else name
                embed.url = scryfall_uri
                embed.set_image(url=art_uri)
                embed.description = f"*{flavor_text}*" if flavor_text else None
                embed.set_footer(text=f"{artist_name} — ™ and © Wizards of the Coast")

                await interaction.send(embed=embed)

            else:
                await interaction.send(
                    f"No art image found for card with name `{name}`."
                )
        else:
            await interaction.send(
                f"No card with name `{name}` from set `{set.upper()}` found."
                if set
                else f"No card with name `{name} found.`"
            )

    @_get_art.on_autocomplete("name")
    async def _card_name_autocomplete(self, interaction, name):
        if name and len(name) > 2:
            autocomplete = scryfall_api.get_autocomplete(name)

            await interaction.response.send_autocomplete(autocomplete.get("data"))
            return
        else:
            await interaction.response.send_autocomplete([])
