import re
import nextcord

from models import MagicCard


def format_custom_emojis(text):
    c_map = {
        # Basic Symbols
        "{W}": "manaw:1018637347941797998",
        "{U}": "manau:1018637747352772698",
        "{B}": "manab:1018638324627410974",
        "{R}": "manar:1018637919768023120",
        "{G}": "manag:1018637911563968592",
        "{C}": "manac:1018637909013827604",
        # Numbers
        "{0}": "mana0:1018638717465935882",
        "{1}": "mana1:1018638718141214841",
        "{2}": "mana2:1018638719676338226",
        "{3}": "mana3:1018638315316072518",
        "{4}": "mana4:1018638316410777720",
        "{5}": "mana5:1018638317736181921",
        "{6}": "mana6:1018638318772174898",
        "{7}": "mana7:1018638319883653231",
        "{8}": "mana8:1018638320969982044",
        "{9}": "mana9:1018638321993383958",
        "{10}": "mana10:1018638323507544234",
        # Phyrexian Mana
        "{W/P}": "manawp:1018637344024313938",
        "{U/P}": "manaup:1018637352823955559",
        "{B/P}": "manabp:1018638328066752666",
        "{R/P}": "manarp:1018637741602377758",
        "{G/P}": "managp:1018637912084062350",
        # Hybrid Generic/Colored
        "{2/W}": "mana2w:1018664005713285131",
        "{2/U}": "mana2u:1018664004383674420",
        "{2/B}": "mana2b:1018638720771035158",
        "{2/R}": "mana2r:1018638723467980942",
        "{2/G}": "mana2g:1018638722125803591",
        # Allied Colors
        "{W/U}": "manawu:1018637342707302571",
        "{U/B}": "manaub:1018637748468461578",
        "{B/R}": "manabr:1018637906887315536",
        "{R/G}": "manarg:1018637738662182933",
        "{G/W}": "managw:1018637915586306058",
        # Enemy Colors
        "{W/B}": "manawb:1018637346796752926",
        "{B/G}": "manabg:1018638325575323709",
        "{G/U}": "managu:1018637913321377822",
        "{U/R}": "manaur:1018637350953295944",
        "{R/W}": "manarw:1018637742797750292",
        # Other Symbols/Mana
        "{S}": "manas:1018637745058488364",
        "{X}": "manax:1018637749173100717",
        "{E}": "manae:1018637910041440317",
        "{T}": "manat:1018637745951887453",
        "{Q}": "manaq:1018637918300024965",
    }

    pattern = re.compile(r'(?<!\w)(' + '|'.join(re.escape(key) for key in c_map.keys()) + r')(?!\w)')
    return pattern.sub(lambda x: f"<:{c_map[x.group()]}>", text)


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
    def get_legality_mark(key):
        if legalities[key] == "legal":
            return '🟢'
        elif legalities[key] == "not_legal":
            return '🔴'
        elif legalities[key] == "restricted":
            return '🟡'
        elif legalities[key] == "banned":
            return '❌'
        return '❓'

    def batch_legalities(formats):
        legality_string = ""

        for format in formats:
            legality_string += f"{format}: {get_legality_mark(format.lower())}\n"

        return legality_string


    formats = [
        "Standard",
        "Pioneer",
        "Modern",
        "Legacy",
        "Vintage",
        "Commander",
        "Historic",
        "Pauper"
    ]

    return batch_legalities(formats)


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

    embed.description = format_custom_emojis(embed.description)

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
            color_string = [format_custom_emojis(cost) for cost in color_string]
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
            color_string = format_custom_emojis(front_face.get("mana_cost"))
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
            color_string = [format_custom_emojis(cost) for cost in color_string]
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
            color_string = format_custom_emojis(raw_card.get("mana_cost"))
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
