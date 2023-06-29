import enum
import inspect
from dataclasses import dataclass, fields

from .base import Coords


class PassiveSkillType(enum.Enum):
    pass


class ActiveSkillType(enum.Enum):
    pass


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


@dataclass(kw_only=True)
class StatedEntity(DataClass):
    name: str
    stats: StatBlock
    active_skill: ActiveSkillType = None
    passive_skill: PassiveSkillType = None

    movement_range: int = 3
    current_movement_range: int = 0
    index: int = 0

    @property
    def is_physical(self):
        return self.stats.calculate_raw("physical_attack") > 0

    def calculate_stat(self, stat_name):
        base = self.stats.calculate_raw(stat_name)
        return int(base + (base * self.stats.tier_modifier))

    def calculate_physical_attack(self):
        return self.calculate_stat("physical_attack")

    def calculate_magical_attack(self):
        return self.calculate_stat("magical_attack")

    def calculate_physical_defense(self):
        return self.calculate_stat("physical_defense")

    def calculate_magical_defense(self):
        return self.calculate_stat("magical_defense")

    def calculate_damage(self, attack, defense):
        return max(1, attack - defense)

    def is_alive(self):
        return self.stats.is_alive()

    def attack(self, attackee: "StatedEntity"):
        if self.is_physical:
            damage = self.calculate_damage(
                self.calculate_physical_attack(), attackee.calculate_physical_defense()
            )
        else:
            damage = self.calculate_damage(
                self.calculate_magical_attack(), attackee.calculate_magical_defense()
            )

        attackee.take_damage(damage)

        return damage

    def take_damage(self, damage):
        self.stats.current_secondary_health -= damage

        if self.stats.current_secondary_health < 0:
            self.stats.current_primary_health += self.stats.current_secondary_health
            self.stats.current_secondary_health = 0

        if self.stats.current_primary_health < 0:
            self.stats.current_primary_health = 0

    def __str__(self):
        return self.name

    def __post_init__(self):
        self.stats.current_primary_health = self.calculate_stat("primary_health")
        self.stats.max_primary_health = self.stats.current_primary_health

        self.stats.current_secondary_health = self.calculate_stat("secondary_health")
        self.stats.max_secondary_health = self.stats.current_secondary_health

        self.current_movement_range = self.movement_range

    def end_turn(self):
        self.current_movement_range = self.movement_range

    def can_use_ability(self):
        return True


@dataclass
class Character(StatedEntity):
    weapon: StatedEntity = None
    artefact: StatedEntity = None

    position: Coords = None

    @property
    def is_physical(self):
        return self.weapon.stats.calculate_raw("physical_attack") > 0

    def calculate_stat(self, stat_name):
        base = 0
        modifier = self.stats.tier_modifier

        for source in (self, self.weapon, self.artefact):
            if source is None:
                continue

            base += source.stats.calculate_raw(stat_name)
            modifier += source.stats.calculate_modifier(stat_name)

        return int(base + (base * modifier))


@dataclass
class Enemy(StatedEntity):
    description: str = None
    position: Coords = None
