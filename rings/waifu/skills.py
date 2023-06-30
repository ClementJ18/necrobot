from dataclasses import dataclass
import enum

from .base import StatBlock


class PassiveSkillType(enum.Enum):
    pass


class ActiveSkillType(enum.Enum):
    pass


@dataclass
class PassiveSkill:
    pass

@dataclass
class ActiveSkill:
    was_activated: bool = False
    was_used: bool = False
    name: str = None
    description: str = None
    cooldown: int = 3

    def on_activation(self, battle, character):
        raise NotImplementedError
    
    def on_attack(self, battle, character, target):
        raise NotImplementedError
    
    def on_end_turn(self, battle, character):
        raise NotImplementedError


@dataclass
class EmpoweredAttack(ActiveSkill):
    stats: StatBlock = None

    def on_attack(self, battle, character, target):
        pass
        

