import enum
import random
from typing import List


class PassiveSkillType(enum.Enum):
    pass


class ActiveSkillType(enum.Enum):
    pass


class StatBlock:
    _primary_health: int
    _secondary_health: int
    _physical_defense: int
    _physical_attack: int
    _magical_defense: int
    _magical_attack: int

    _tier: int

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(f"_{key}", value)

    def __getattribute__(self, name: str):
        attr = object.__getattribute__(f"_{name}")
        if isinstance(attr, int):
            return attr

        return object.__getattribute__(name)


class Character:
    name: str
    stats: StatBlock
    weapon: "Character"
    artefact: "Character"
    active_skill: ActiveSkillType
    passive_skill: PassiveSkillType


class Terrain:
    pass


class Event:
    pass


class Battle:
    players: List[Character]
    enemies: List[Character]
    terrain: Terrain
    event: Event

    used_last_turn: List[Character]

    def can_move_this_turn(self, char: Character):
        return char not in self.used_last_turn

    def pick_enemies(self):
        valid_list = [enemy for enemy in self.enemies if enemy not in self.used_last_turn]
        return random.sample(valid_list, len(valid_list) // 3)
