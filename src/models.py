import datetime
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel


class MagicCard(BaseModel):
    name: str
    color_identity: Tuple[Any, ...]
    normal_image_url: str
    normal_image_bytes: bytes
    oracle_text: Optional[str]
    flavor_text: Optional[str]
    scryfall_uri: str
    color_string: Optional[str]
    type_line: Optional[str]
    power: Optional[str]
    toughness: Optional[str]
    loyalty: Optional[str]
    prices: Optional[Dict[str, Any]]
    set: Optional[str]
    set_name: Optional[str]
    legalities: Optional[Dict[str, str]]

class MagicCardRuling(BaseModel):
    published_at: datetime.date
    source: str
    comment: str
