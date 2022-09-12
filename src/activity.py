from asyncio import tasks
from random import choice
from nextcord import Game
from nextcord.ext import commands, tasks


class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activities = [
            "top 8 at F2F",
            "against Tron and losing",
            "the pack lottery",
            "Cockatrice",
            "Market Speculation 101",
            "against burn",
            "against control and suffering",
            "with dice",
            "in garbage time",
            "vintage cube draft",
            "against That Guy™",
            "against Abzan Greasefang",
            "against Greasefang with a Leyline",
            "at FNM",
            "proxied legacy",
            "with my opponent's feelings 🥺",
            "manaless dredge",
            "Thoughtseize turn 1",
            "monke on 1",
            "the topdecking game",
        ]

        self.activity.start()

    def cog_unload(self):
        self.activity.cancel()

    @tasks.loop(minutes=5.0)
    async def activity(self):
        activity = Game(name=choice(self.activities))

        await self.bot.change_presence(activity=activity)

    @activity.before_loop
    async def before_activity(self):
        await self.bot.wait_until_ready()
