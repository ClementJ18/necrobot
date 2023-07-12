from __future__ import annotations

from dataclasses import dataclass
import enum
from typing import Union, TYPE_CHECKING

from .base import DamageInstance, get_distance
from .base import DamageInstance, StatBlock

if TYPE_CHECKING:
    from .battle import Battle
    from .entities import StattedEntity


class PassiveSkillType(enum.Enum):
    pass


class ActiveSkillType(enum.Enum):
    pass


@dataclass
class Skill:
    name: str = None
    description: str = None

    def on_attack(self, battle: Battle, entity: StattedEntity, attackee: StattedEntity):
        """This is triggered when an entity declares an attack"""
        pass

    def on_defend(self, battle: Battle, entity: StattedEntity, attacker: StattedEntity):
        """This is triggered when an entity is declared an attack on."""
        pass

    def on_calculate_attack(
        self, entity: StattedEntity, attackee: StattedEntity, current_attack: int, physical: bool
    ):
        """This is triggered when calculating stats to determine the final
        attack stat. The returned value is added to the rest."""
        return 0

    def on_calculate_defense(
        self, entity: StattedEntity, attacker: StattedEntity, current_defense: int, physical: bool
    ):
        """This is triggered when calculating stats to determine the final
        defense stat. The returned value is added to the rest."""
        return 0

    def on_take_damage(
        self, entity: StattedEntity, attacker: StattedEntity, damage: DamageInstance
    ):
        """This is triggered when damage is taken. The return of this is the final damage.

        This value is not affected by modifier, often called "true" damage.
        """
        return damage

    def on_deal_damage(
        self, entity: StattedEntity, attackee: StattedEntity, damage: DamageInstance
    ):
        """This is triggered when damage is dealt. The return of this is the final damage.

        This value is not affected by modifier, often called "true" damage."""
        return damage

    def on_end_turn(self, battle: Battle, entity: StattedEntity):
        """This is triggered at the end of the turn before the entities are
        incremented."""
        pass

    def on_start_turn(self, battle: Battle, entity: StattedEntity):
        """This is triggered at the start of a turn, right after entities have been
        incremented."""
        pass

    def on_activation(self, battle: Battle, entity: StattedEntity):
        """This is triggered when the active ability of the entity is used."""
        pass


"""The main difference between an active and passive skill is the cooldown.
- Passive skills trigger at every possible instance and have no cooldowns.
- Active skill only trigger when activated and enter a cooldown after
"""


@dataclass(eq=False)
class Modifier(Skill):
    duration: int = 0
    can_duplicate: bool = False
    can_stack: bool = False

    def end_turn(self):
        self.duration -= 1

        return self.is_expired()

    def is_expired(self):
        return self.duration < 1

    def __eq__(self, other: Modifier) -> bool:
        return self.name == other.name


@dataclass
class PassiveSkill(Skill):
    pass


@dataclass
class ActiveSkill(Skill):
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


@dataclass
class ShieldPiercing(PassiveSkill):
    def on_deal_damage(
        self, entity: StattedEntity, attackee: StattedEntity, damage: DamageInstance
    ):
        damage.secondary = False
        return damage


@dataclass
class ConsecutiveAttacks(PassiveSkill):
    last_attacked: StattedEntity = None
    times_attacked: int = 0
    stats: StatBlock = None

    def on_attack(self, battle: Battle, entity: StattedEntity, attackee: StattedEntity):
        if self.last_attacked is None or self.last_attacked != attackee:
            self.last_attacked = attackee
            self.times_attacked = 0
        else:
            self.times_attacked += 1

    def on_calculate_attack(
        self, entity: StattedEntity, attackee: StattedEntity, current_attack: int, physical: bool
    ):
        stat = "physical_attack" if physical else "magical_attack"

        if self.stats.stat_is_raw(stat):
            return min(self.times_attacked, self.stats.calculate_raw(stat) * self.times_attacked)

        return min(
            self.times_attacked,
            self.stats.calculate_modifier(stat) * current_attack * self.times_attacked,
        )


@dataclass
class EmpoweredAttack(ActiveSkill):
    stats: StatBlock = None

    def on_calculate_attack(
        self, entity: StattedEntity, attackee: StattedEntity, current_attack: int, physical: bool
    ):
        self.put_on_cooldown()
        stat = "physical_attack" if physical else "magical_attack"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_attack


@dataclass
class GrantShield(ActiveSkill):
    shield_amount: int = 0

    def on_activation(self, battle: Battle, entity: StattedEntity):
        for player in battle.players:
            player.grant_health(self.shield_amount, secondary=True, respect_max=False)

        self.put_on_cooldown()


@dataclass
class ChangeDamageType(ActiveSkill):
    currently_physical: bool = True

    def on_activation(self, battle: Battle, entity: StattedEntity):
        self.currently_physical = not self.currently_physical


@dataclass
class DefensiveBuff(Modifier):
    stats: StatBlock = None

    def on_calculate_defense(
        self, entity: StattedEntity, attacker: StattedEntity, current_defense: int, physical: bool
    ):
        stat = "physical_defense" if physical else "magical_defense"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_defense


@dataclass
class MapWideAura(PassiveSkill):
    turns: int = 0
    stats: StatBlock = None

    def on_start_turn(self, battle: Battle, entity: StattedEntity):
        for e in battle.players:
            if entity == e:
                continue

            e.add_modifier(DefensiveBuff(duration=self.turns, stats=self.stats, name=self.name))


@dataclass
class OffensiveBuff(Modifier):
    stats: StatBlock = None

    def on_calculate_attack(
        self, entity: StattedEntity, attacker: StattedEntity, current_attack: int, physical: bool
    ):
        stat = "physical_attack" if physical else "magical_attack"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_attack


@dataclass
class GrantStatBoost(ActiveSkill):
    stats: StatBlock = None
    distance: int = 1
    turns: int = 0

    def on_activation(self, battle: Battle, entity: StattedEntity):
        for e in battle.players:
            if entity == e:
                continue

            if get_distance(e.position, entity.position) <= self.distance:
                e.add_modifier(
                    OffensiveBuff(duration=self.turns, stats=self.stats, name=self.name)
                )


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
        "description": "The wielder winds up their trident before striking a powerful blow with increased physical damage.",
    },
    "Ghostly Reach": {
        "values": {},
        "class": ShieldPiercing,
        "description": "The character's attacks pierce through armor and magical shields, reaching out directly to the vitality of its target.",
    },
    "Scholar": {
        "values": {"stats": StatBlock(physical_attack=(True, 5), magical_attack=(True, 5))},
        "class": ConsecutiveAttacks,
        "description": "Every time this character attack the same enemy as last turn they gain a small stacking boost in damage.",
    },
    "Aura of the Smith": {
        "values": {"turns": 1, "stats": StatBlock(physical_defense=(True, 10))},
        "class": MapWideAura,
        "description": "The knowledge of the smith boosts the physical defense of all allies on the map",
    },
    "Presence of the Smith": {
        "values": {"turns": 5, "stats": StatBlock(physical_attack=(True, 15))},
        "class": GrantStatBoost,
        "description": "When activated, all allies adjacent to the smith gain a long lasting buff to their physical attack",
    },
}
