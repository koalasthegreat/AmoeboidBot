# AmoeboidBot

A simple Magic the Gathering card Discord bot.

When a card name is wrapped in square brackets, the bot will reply with data about the card and an image of it.

## Commands
- `rulings <arg>`: Displays the rulings for the given card, if they exist.
- `wrapping <arg=None>:`: If given an argument, changes the wrapping for detecting cards in the server it was run. Otherwise, shows the current wrapping. Usable only by administrators.

## Setup
Copy `.env.dist` to a file called `.env`, and fill out the given fields. Then, run your bot with `python bot.py`.