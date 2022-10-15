from asyncio import tasks
from random import choice
from nextcord import ActivityType 
import nextcord
from nextcord.ext import commands, tasks


class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activities = [
            { "name": "top 8 at F2F", "type": "playing" },
            { "name": "against Tron and losing", "type": "playing" },
            { "name": "the pack lottery", "type": "playing" },
            { "name": "Cockatrice", "type": "playing" },
            { "name": "Market Speculation 101", "type": "playing" },
            { "name": "against burn", "type": "playing" },
            { "name": "against control and suffering", "type": "playing" },
            { "name": "with dice", "type": "playing" },
            { "name": "in garbage time", "type": "playing" },
            { "name": "vintage cube draft", "type": "playing" },
            { "name": "against That Guy™", "type": "playing" },
            { "name": "against Abzan Greasefang", "type": "playing" },
            { "name": "against Rakdos Midrange again", "type": "playing" },
            { "name": "at FNM", "type": "playing" },
            { "name": "proxied legacy", "type": "playing" },
            { "name": "with my opponent's feelings 🥺", "type": "playing" },
            { "name": "manaless dredge", "type": "playing" },
            { "name": "Thoughtseize turn 1", "type": "playing" },
            { "name": "monke on 1", "type": "playing" },
            { "name": "the topdecking game", "type": "playing" },

            { "name": "AspiringSpike on Twitch", "type": "watching" },
            { "name": "MagicAids on YouTube", "type": "watching" },
            { "name": "YungDingo on Twitch", "type": "watching" },
            { "name": "AndreaMengucci on Twitch", "type": "watching" },
            { "name": "yellowhat on Twitch", "type": "watching" },

            { "name": "to my opponent whine", "type": "listening" },
        ]

        self.activity.start()

    def cog_unload(self):
        self.activity.cancel()

    @tasks.loop(minutes=20.0)
    async def activity(self):
        selection = choice(self.activities)
        activity: BaseException

        if selection["type"] == "playing":
            activity = nextcord.Activity(name=selection["name"], type=ActivityType.playing)
        if selection["type"] == "streaming":
            activity = nextcord.Activity(name=selection["name"], type=ActivityType.streaming)
        if selection["type"] == "listening":
            activity = nextcord.Activity(name=selection["name"], type=ActivityType.listening)
        if selection["type"] == "watching":
            activity = nextcord.Activity(name=selection["name"], type=ActivityType.watching)

        await self.bot.change_presence(activity=activity)

    @activity.before_loop
    async def before_activity(self):
        await self.bot.wait_until_ready()
