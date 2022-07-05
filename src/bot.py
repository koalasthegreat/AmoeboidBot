import os
import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

from events import Events
from botcommands import Artwork, Rulings, Settings


load_dotenv()
TOKEN = os.getenv("TOKEN")
DEFAULT_WRAPPING = os.getenv("DEFAULT_WRAPPING", default="[[*]]")
DB_NAME = os.getenv("DB_NAME", default="bot.db")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", default=24))


intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(intents=intents)
bot.add_cog(Settings(bot))
bot.add_cog(Rulings(bot))
bot.add_cog(Artwork(bot))
bot.add_cog(Events(bot))

bot.run(TOKEN)
