import re
import nextcord

from models import MagicCard


def format_color_string(cost):
    c_map = {"R": "🔴", "U": "🔵", "G": "🟢", "B": "🟣", "W": "⚪", "C": "⟡"}
    curly_brace_regex = r"\{(.*?)\}"

    formatted_string = ""
    arr = re.findall(curly_brace_regex, cost)

    for cost_symbol in arr:
        if cost_symbol in c_map:
            formatted_string += c_map[cost_symbol]
        else:
            formatted_string += f"({cost_symbol})"

    return f"**{formatted_string}**" if formatted_string != "" else ""


def format_color_identity(color):
    color_map = {
        "R": (221, 46, 68),
        "U": (85, 172, 238),
        "G": (120, 177, 89),
        "B": (49, 55, 61),
        "W": (230, 231, 232),
        "C": (100, 101, 102),
    }

    if len(color) == 0:
        return (100, 101, 102)

    if len(color) == 1:
        color = color[0]
        if color in color_map:
            return color_map[color]

    else:
        return (207, 181, 59)


def make_legality_string(legalities):
    def get_entry_value(key):
        if legalities[key] == "legal":
            return True
        return False

    legality_string = ""

    legality_string += f"Standard: {'🟢' if get_entry_value('standard') else '🔴'}\n"
    legality_string += f"Pioneer: {'🟢' if get_entry_value('pioneer') else '🔴'}\n"
    legality_string += f"Modern: {'🟢' if get_entry_value('modern') else '🔴'}\n"
    legality_string += f"Legacy: {'🟢' if get_entry_value('legacy') else '🔴'}\n"
    legality_string += f"Vintage: {'🟢' if get_entry_value('vintage') else '🔴'}\n"
    legality_string += f"Commander: {'🟢' if get_entry_value('commander') else '🔴'}\n"
    legality_string += f"Historic: {'🟢' if get_entry_value('historic') else '🔴'}\n"
    legality_string += f"Pauper: {'🟢' if get_entry_value('pauper') else '🔴'}"

    return legality_string


def format_prices(prices):
    price_string = ""
    usd = prices.get("usd")
    usd_foil = prices.get("usd_foil")

    if usd:
        price_string += "Normal: " + (prices.get("usd") or "N/A") + " USD\n"
    else:
        price_string += "Normal: N/A\n"
    if usd_foil:
        price_string += "Foil: " + (prices.get("usd_foil") or "N/A") + " USD"
    else:
        price_string += "Foil: N/A"

    return price_string


def generate_embed(card):
    embed = nextcord.Embed(type="rich")
    embed.title = card.name

    prefix = ""

    embed.description = ""

    if card.oracle_text is not None:
        embed.description += card.oracle_text

    if embed.description != "":
        prefix = "\n\n"

    if card.flavor_text is not None:
        embed.description += f"{prefix}*{card.flavor_text}*"

    if embed.description != "":
        embed.description += f"\n\n[View on Scryfall]({card.scryfall_uri})"

    r, g, b = card.color_identity
    embed.colour = nextcord.Color.from_rgb(r, g, b)

    if card.color_string is not None and card.color_string != "":
        embed.add_field(name="Cost:", value=card.color_string)

    if card.type_line is not None:
        embed.add_field(name="Type:", value=card.type_line)

    if card.loyalty is not None:
        embed.add_field(name="Loyalty:", value=card.loyalty)

    if card.power is not None:
        embed.add_field(name="Stats:", value=f"{card.power}/{card.toughness}")

    if card.set is not None and card.set_name is not None:
        set_string = f"[{card.set.upper()}] {card.set_name}"
        embed.add_field(name="Set:", value=set_string)

    if card.prices is not None:
        price_string = format_prices(card.prices)
        embed.add_field(name="Prices:", value=price_string)

    if card.legalities is not None:
        legalities = make_legality_string(card.legalities)
        embed.add_field(name="Legalities:", value=legalities)

    return embed

def process_raw_cards(raw_cards):
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
    
    return cards
