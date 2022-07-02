import os
from nextcord.ext import commands
from dotenv import load_dotenv

from events import Events
from botsettings import bot_settings
from botcommands import Artwork, Rulings, Settings


load_dotenv()
TOKEN = os.getenv("TOKEN")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", default="a!")
DEFAULT_WRAPPING = os.getenv("DEFAULT_WRAPPING", default="[[*]]")
DB_NAME = os.getenv("DB_NAME", default="bot.db")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", default=24))


def get_prefix(client, message):
    if not message.guild:
        return DEFAULT_PREFIX
    return bot_settings.get_prefix(message.guild.id)


bot = commands.Bot(command_prefix=get_prefix)
bot.add_cog(Settings(bot))
bot.add_cog(Rulings(bot))
bot.add_cog(Artwork(bot))
bot.add_cog(Events(bot))

bot.run(TOKEN)
