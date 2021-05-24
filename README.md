# AmoeboidBot

A simple Magic the Gathering card Discord bot.

When a card name is wrapped in square brackets, the bot will reply with data about the card and an image of it.

## Commands
- `rulings <arg>`: Displays the rulings for the given card, if they exist.
- `prefix <arg=None>`: If given an argument, changes the bot prefix for the server it was run in, otherwise, shows the current prefix. Usable only by administrators.
- `wrapping <arg=None>:`: If given an argument, changes the wrapping for detecting cards in the server it was run. Otherwise, shows the current wrapping. Usable only by administrators.

## Setup
You will need a compiled [spellfix](https://www.sqlite.org/spellfix1.html) version in the root directory of the project to run this bot.

As well, copy `.env.dist` to a file called `.env`, and fill out the given fields, including your Discord bot token, and TCGPlayer API tokens. Then, run the bot with `python bot.py`.