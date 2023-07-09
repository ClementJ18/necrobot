from collections import namedtuple
from dataclasses import dataclass, fields
import inspect
from typing import Tuple

Coords = Tuple[int, int]  # (x, y)
Size = namedtuple("Size", "length height")

POSITION_EMOJIS = [
    ":zero:",
    ":one:",
    ":two:",
    ":three:",
    ":four:",
    ":five:",
    ":six:",
    ":seven:",
    ":eight:",
    ":nine:",
]


def get_distance(origin: Coords, destination: Coords):
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    return abs(dx) + abs(dy)


def get_symbol(index):
    return f"{index}\ufe0f\N{COMBINING ENCLOSING KEYCAP}"


@dataclass
class DamageInstance:
    """This class defines a damage instance which is an easy
    way of passing and manipulating data related to damage between
    the different methods and calls."""

    amount: int
    secondary: bool = True

    def finalise(self):
        self.amount = int(self.amount)


class DataClass:
    @classmethod
    def from_dict(cls, env):
        return cls(**{k: v for k, v in env.items() if k in inspect.signature(cls).parameters})


@dataclass
class Stat:
    is_percent: bool
    stat: float

    @property
    def modifier(self):
        if not self.is_percent:
            return 0

        return self.stat

    @property
    def raw(self):
        if self.is_percent:
            return 0

        return self.stat

    def to_db(self):
        return self.to_list()

    @classmethod
    def from_db(cls, record):
        return cls(*record)

    def to_list(self):
        return (self.is_percent, self.stat)

    def __str__(self) -> str:
        if self.is_percent:
            return f"+{self.stat}%"

        return str(self.stat)


@dataclass
class StatBlock(DataClass):
    primary_health: Stat = Stat(False, 0)
    secondary_health: Stat = Stat(False, 0)
    physical_defense: Stat = Stat(False, 0)
    physical_attack: Stat = Stat(False, 0)
    magical_defense: Stat = Stat(False, 0)
    magical_attack: Stat = Stat(False, 0)

    tier: int = 0

    current_primary_health: int = 0
    current_secondary_health: int = 0
    max_primary_health: int = 0
    max_secondary_health: int = 0

    @property
    def tier_modifier(self):
        return 0.02 * self.tier

    def is_alive(self):
        return self.current_primary_health > 0

    def __post_init__(self):
        for f in fields(self):
            if not f.type is Stat:
                continue

            value = getattr(self, f.name)
            if not isinstance(value, f.type):
                setattr(self, f.name, f.type(*value))

    def calculate_raw(self, stat_name):
        stat: Stat = getattr(self, stat_name)
        if stat is None:
            raise AttributeError(f"{stat_name} not a valid stat")

        return stat.raw

    def calculate_modifier(self, stat_name):
        stat: Stat = getattr(self, stat_name)
        if stat is None:
            raise AttributeError(f"{stat_name} not a valid stat")

        return stat.modifier / 100

    def stat_is_raw(self, stat_name):
        return not getattr(self, stat_name).is_percent


"""
{
        "name": "",
        "image_url": "",
        "description": "",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
"""


DUD_TEMPLATES = [
    {
        "name": "Bag of Goodies",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116482199466819695/HReach-HealthPack.png",
        "description": "A bag containing some goodies, good to eat but not for much else.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Ancient Blade",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116707849876275260/462px-Weapon_b_1020002200.png",
        "description": "An old sword, very finely crafted but dulled by time.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Broken Hourglass",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116718269496299520/desktop-wallpaper-fantasy-artistic-video-game-sand-clock.png",
        "description": "This hourglass used to be able to tell the time with no equal but ever since the glass was shattered it has been abandoned.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Shattered Crown",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116797755659128923/Broken_Crown_icon.png",
        "description": "The crown of the empress of an long forgotten empire. It is said she wore it till she was betrayed by her own knights. The killing blow shattered the crown and doomed the kingdom.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Rusty Goblet",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116799230338662480/public.png",
        "description": "This goblet sat on the table of the many kings of an ancient realm before it fell to the forces of evil.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "The Twin Dragons",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116800827185696778/latest.png",
        "description": "A dirty medallion, long ago it held power of life itself. Roughly welded together, the pieces were used in a dark ritual before being discarded.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Tablets of the Arbiter",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116814455829971148/latest.png",
        "description": "An ancient tablet, a powerful tool used by the Arbiter to defeat his enemies. Now, long after his death, it is just a shattered pile of stone.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Splintered Síoraíocht",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1116816978523455498/636284768481526959.png",
        "description": "The flame staff was once a symbol of power of an entire civilisation, it was taken away when that civilisation fell in a fool hope. Now its owner lays dead and the staff has been splintered.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Extinguished Silverlight",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1117099808822407268/glass_weapon_7_by_rittik_designs-d895tzq.png",
        "description": "Once the blade of a powerful king, its light faded when the great darkness swept over the land, the likes of it never to be again.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Thawed Frostpear",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1117116745736523827/Select20a20file20name20for20output20files_004.png",
        "description": "This wet spear was once a great frost spear, wielded by the mightiest of Dragon-knights. Bathed in demonic flames during the Cataclysm, its icy point thawed and its power was undone.",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
    {
        "name": "Failnaught",
        "image_url": "https://cdn.discordapp.com/attachments/318465643420712962/1117182929311899789/latest.png",
        "description": "A dull, unstrung bow. Age has faded the ornate painting on the wood and rendered it brittle. ",
        "tier": 0,
        "universe": "Nexus",
        "title": "*Poof*",
        "modifier": 1,
    },
]
