import discord
from discord.ext import commands
from time import sleep
import os
import json
import requests
import asyncio
import re
from dotenv import load_dotenv

# load .env
load_dotenv()
TOKEN = os.getenv('TOKEN')
PREFIX = os.getenv('PREFIX', default='a!')

# init bot
bot = commands.Bot(command_prefix = PREFIX)


# queries scryfall for a card, returning the result
def getCard(name):
    payload = {"fuzzy": name}

    r = requests.get('https://api.scryfall.com/cards/named', params=payload)
    
    parsed = json.loads(r.content)

    return parsed

# formats and returns the cost string for a card
def getCostString(cost):
    formatted_string = ""
    arr = cost.split("{")

    for char in arr:
        if len(char) != 0:
            c = char[0]
            
            try:
                int(c)
                formatted_string += "**(" + c + ")**"
                

            except ValueError:
                if c == "R":
                    formatted_string += "🔴"
                elif c == "U":
                    formatted_string += "🔵"
                elif c == "G":
                    formatted_string += "🟢"
                elif c == "B":
                    formatted_string += "⚫"
                else:
                    formatted_string += "⚪"

    return formatted_string

# gets color from a color identity string
def getColorIdentity(color):
    if len(color) == 0:
        return discord.Color.from_rgb(100,101,102)

    if len(color) == 1:
        color = color[0]
        if color == "R":
            return discord.Color.from_rgb(221,46,68)
        elif color == "U":
            return discord.Color.from_rgb(85,172,238)
        elif color == "G":
            return discord.Color.from_rgb(120,177,89)
        elif color == "B":
            return discord.Color.from_rgb(49,55,61)
        elif color == "W":
            return discord.Color.from_rgb(230,231,232)
    else:
        return discord.Color.from_rgb(207,181,59)

# formats the embed for a card
def formatEmbed(card):
    embed = discord.Embed(type="rich")
    if card.get('name') is None:
        print("ERROR: Card not found")
        return None
    else:
        embed.title = card['name']
        if card.get('color_identity') is not None:
            embed.colour = getColorIdentity(card['color_identity'])
        if card.get('image_uris').get('normal') is not None:
            embed.set_image(url=card['image_uris']['normal'])
        if card.get('oracle_text') is not None:
            embed.description = card['oracle_text']
        if card.get('flavor_text') is not None:
            if embed.description != "":
                embed.description += "\n\n*" + card['flavor_text'] + "*"
            else:
                embed.description = "*" + card['flavor_text'] + "*"
        if card.get('scryfall_uri') is not None:
            if embed.description != "":
                embed.description += "\n\n [View on Scryfall](" + card['scryfall_uri'] + ")" 
        if card.get('mana_cost') is not None:
            embed.add_field(name="Cost:", value=getCostString(card['mana_cost']))
        if card.get('type_line') is not None:
            embed.add_field(name="Type:", value=card['type_line'])
        if card.get('power') is not None and card.get('toughness') is not None:
            embed.add_field(name="Stats:", value=card['power'] + "/" + card['toughness'])
        if card.get('loyalty') is not None:
            embed.add_field(name="Loyalty:", value=card['loyalty'])
        return embed

@bot.event
async def on_ready():
    print("Bot is online")

@bot.event
async def on_message(message):
    if "[" in message.content and not message.author.bot:
        count = 0

        regex = r"\[(.*?)\]"
        card_names = re.findall(regex, message.content)

        cards = []

        for name in card_names:
            card = getCard(name)
            cards.append(card)
            sleep(0.200)

        for card in cards:
            if count >= 5:
                await message.channel.send("To prevent spam, only 5 cards can be processed at one time. Please make another query.")
                break

            count += 1
            embed = formatEmbed(card)
            await message.channel.send(embed=embed)
            await asyncio.sleep(1)


bot.run(TOKEN)