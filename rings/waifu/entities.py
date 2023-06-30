from dataclasses import dataclass

from .base import Coords, DataClass, StatBlock
from .skills import PassiveSkill, ActiveSkill


@dataclass(kw_only=True)
class StatedEntity(DataClass):
    name: str
    stats: StatBlock
    active_skill: ActiveSkill = None
    passive_skill: PassiveSkill = None

    movement_range: int = 3
    current_movement_range: int = 0
    index: int = 0
    has_used_active_skill: bool = False

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
