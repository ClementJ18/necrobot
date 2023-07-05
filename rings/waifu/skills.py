from dataclasses import dataclass
import enum
from typing import Union

from .base import DamageInstance, StatBlock


class PassiveSkillType(enum.Enum):
    pass


class ActiveSkillType(enum.Enum):
    pass


@dataclass
class PassiveSkill:
    pass


@dataclass
class ActiveSkill:
    name: str = None
    description: str = None
    cooldown: int = 3

    was_activated: bool = False
    current_cooldown: int = 0

    def can_activate(self):
        return (not self.was_activated) and self.current_cooldown == 0

    def is_active(self):
        return self.was_activated and self.current_cooldown == 0

    def put_on_cooldown(self):
        self.current_cooldown = self.cooldown
        self.was_activated = False

    def end_turn(self):
        self.was_activated = False
        if self.current_cooldown > 0:
            self.current_cooldown -= 1

    def on_activation(self, battle, character):
        """This is triggered when the button is clicked"""
        pass

    def on_attack(self, battle, character, attackee):
        """This is triggered when an entity declares an attack"""
        pass

    def on_defend(self, battle, character, attacker):
        """This is triggered when an entity is declared an attack on."""
        pass

    def on_calculate_attack(self, character, attackee, current_attack, physical: bool):
        """This is triggered when calculating stats to determine the final
        attack stat. The returned value is added to the rest."""
        return 0

    def on_calculate_defense(self, character, attacker, current_defense, physical: bool):
        """This is triggered when calculating stats to determine the final
        defense stat. The returned value is added to the rest."""
        return 0

    def on_take_damage(self, character, attacker, damage: DamageInstance):
        """This is triggered when damage is taken. The return of this is the final damage.

        This value is not affected by modifier, often called "true" damage.
        """
        return damage

    def on_deal_damage(self, character, attackee, damage: DamageInstance):
        """This is triggered when damage is dealt. The return of this is the final damage.

        This value is not affected by modifier, often called "true" damage."""
        return damage

    def on_end_turn(self, battle, character):
        """This is triggered at the end of the turn."""
        pass


@dataclass
class EmpoweredAttack(ActiveSkill):
    stats: StatBlock = None

    def on_calculate_attack(self, character, attackee, current_attack, physical: bool):
        self.put_on_cooldown()
        stat = "physical_attack" if physical else "magical_attack"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_attack


@dataclass
class GrantShield(ActiveSkill):
    shield_amount: int = 0

    def on_activation(self, battle, character):
        for player in battle.players:
            player.grant_health(self.shield_amount, secondary=True, respect_max=False)

        self.put_on_cooldown()


def get_skill(name) -> Union[ActiveSkill, PassiveSkill]:
    skill = SKILLS.get(name)
    if skill is None:
        return None

    return skill["class"](name=name, description=skill["description"], **skill["values"])


SKILLS = {
    "Ethereal Protection": {
        "values": {"shield_amount": 15},
        "class": GrantShield,
        "description": "A shield envelopes all players on the field.",
    },
    "Trident Strike": {
        "values": {"stats": StatBlock(physical_attack=(False, 15))},
        "class": EmpoweredAttack,
        "description": "The wielder winds up his trident before striking a powerful blow with increased physical damage.",
    },
}
