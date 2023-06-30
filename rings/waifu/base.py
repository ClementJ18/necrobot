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


def get_symbol(index):
    return f"{index}\ufe0f\N{COMBINING ENCLOSING KEYCAP}"


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
    primary_health: Stat
    secondary_health: Stat = (False, 0)
    physical_defense: Stat = (False, 0)
    physical_attack: Stat = (False, 0)
    magical_defense: Stat = (False, 0)
    magical_attack: Stat = (False, 0)

    tier: int = 0

    current_primary_health: int = 0
    current_secondary_health: int = 0
    max_primary_health: int = 0
    max_secondary_health: int = 0

    @property
    def tier_modifier(self):
        return 0.02 * self.tier

    def is_alive(self):
        return self.current_primary_health > 0 or self.current_secondary_health > 0

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
