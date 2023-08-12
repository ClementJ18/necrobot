from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Type, Union

from .base import DamageInstance, StatBlock, get_distance

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
    ) -> int:
        """This is triggered when calculating stats to determine the final
        attack stat. The returned value is added to the rest."""
        return 0

    def on_calculate_defense(
        self, entity: StattedEntity, attacker: StattedEntity, current_defense: int, physical: bool
    ) -> int:
        """This is triggered when calculating stats to determine the final
        defense stat. The returned value is added to the rest."""
        return 0

    def on_take_damage(
        self, entity: StattedEntity, attacker: StattedEntity, damage: DamageInstance
    ) -> int:
        """This is triggered when damage is taken. The return of this is the final damage.

        This value is not affected by modifier, often called "true" damage.
        """
        return damage

    def on_deal_damage(
        self, entity: StattedEntity, attackee: StattedEntity, damage: DamageInstance
    ) -> int:
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

    def on_generate_target_list(
        self,
        battle: Battle,
        owner: StattedEntity,
        entity: StattedEntity,
        potential_targets: List[StattedEntity],
    ):
        """This is triggered when we create the list of possible targets. This is useful for restricting
        who we target. owner is the entity the list is being generated for, entity is the entity that the
        skill/modifier belongs to and potential_targets is the list to be modified.
        """
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
class MapWideAura(PassiveSkill):
    turns: int = 0
    stats: StatBlock = None
    allowed_char: List[str] = ()

    def on_start_turn(self, battle: Battle, entity: StattedEntity):
        for e in battle.players:
            if entity == e:
                continue

            if self.allowed_char and not entity.name in self.allowed_char:
                continue

            e.add_modifier(GrantBuff(duration=self.turns, stats=self.stats, name=self.name))


@dataclass
class GrantModifierInArea(ActiveSkill):
    stats: StatBlock = None
    distance: int = 1
    turns: int = 0
    modifier: Type[Modifier] = None

    def on_activation(self, battle: Battle, entity: StattedEntity):
        for e in battle.players:
            if entity == e:
                continue

            if get_distance(e.position, entity.position) <= self.distance:
                e.add_modifier(
                    self.modifier(duration=self.turns, stats=self.stats, name=self.name)
                )


@dataclass
class GrantBuff(Modifier):
    stats: StatBlock = None

    def on_calculate_defense(
        self, entity: StattedEntity, attacker: StattedEntity, current_defense: int, physical: bool
    ):
        stat = "physical_defense" if physical else "magical_defense"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_defense

    def on_calculate_attack(
        self, entity: StattedEntity, attacker: StattedEntity, current_attack: int, physical: bool
    ):
        stat = "physical_attack" if physical else "magical_attack"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_attack


def grant_health(entity: StattedEntity, stats: StatBlock):
    for stat in ("primary_health", "secondary_health"):
        secondary = stat == "secondary_health"
        if stats.stat_is_raw(stat):
            entity.grant_health(stats.calculate_raw(stat), secondary=secondary)
        else:
            entity.grant_health(
                stats.calculate_modifier(stat) * entity.stats.calculate_raw(stat),
                secondary=secondary,
            )


@dataclass
class GrantHealth(Modifier):
    stats: StatBlock = None

    def on_start_turn(self, battle: Battle, entity: StattedEntity):
        grant_health(entity, self.stats)


@dataclass
class RecoverHealth(PassiveSkill):
    stats: StatBlock = None

    def on_end_turn(self, battle: Battle, entity: StattedEntity):
        grant_health(entity, self.stats)


@dataclass
class OnHitModifier(PassiveSkill):
    stats: StatBlock = None
    turns: int = 1
    modifier: Type[Modifier] = None

    def on_attack(self, battle: Battle, entity: StattedEntity, attackee: StattedEntity):
        return attackee.add_modifier(self.modifier(name=self.name, duration=self.turns))


@dataclass
class Rivalry(PassiveSkill):
    last_enemy: StattedEntity = None
    stats: StatBlock = None

    def on_defend(self, battle: Battle, entity: StattedEntity, attacker: StattedEntity):
        self.last_enemy = attacker

    def on_calculate_attack(
        self, entity: StattedEntity, attackee: StattedEntity, current_attack: int, physical: bool
    ):
        if attackee != self.last_enemy:
            return 0

        stat = "physical_attack" if physical else "magical_attack"

        if self.stats.stat_is_raw(stat):
            return self.stats.calculate_raw(stat)

        return self.stats.calculate_modifier(stat) * current_attack


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
        "values": {
            "turns": 5,
            "stats": StatBlock(physical_attack=(True, 15)),
            "modifier": GrantBuff,
        },
        "class": GrantModifierInArea,
        "description": "When activated, all allies adjacent to the smith gain a long lasting buff to their physical attack",
    },
    "Strength of the Heat": {
        "values": {"turns": 1, "stats": StatBlock(magical_defense=(True, 10))},
        "class": MapWideAura,
        "description": "The mere presence of the Nether Dweller reinforces the flow of magic, granting his allies more resistance",
    },
    "Fiery Aura": {
        "values": {
            "turns": 5,
            "stats": StatBlock(magical_attack=(True, 15)),
            "modifier": GrantBuff,
        },
        "class": GrantModifierInArea,
        "description": "The fiery aura of the Nether Dweller flares, envelopping all those around him in it's power and granting them increase magical offense.",
    },
    "Refreshing Drinks": {
        "values": {
            "turns": 5,
            "stats": StatBlock(primary_health=(True, 5)),
            "modifier": GrantHealth,
        },
        "class": GrantModifierInArea,
        "description": "Where ever the Barman goes he bring with him many refreshing drinks that he happily shares",
    },
    "Ender Sword": {
        "values": {
            "turns": 1,
            "stats": StatBlock(magical_defense=(True, -50)),
            "modifier": GrantBuff,
        },
        "class": OnHitModifier,
        "description": "The End Walker's sword is made from material that syphon magic, draining the hit enemies of their magical resistances",
    },
    "Merman Leader": {
        "values": {
            "turns": 1,
            "stats": StatBlock(physical_attack=(True, 10), physical_defense=(True, 5)),
            "modifier": GrantBuff,
            "allowed_char": ("The Merman",),
        },
        "class": MapWideAura,
        "description": "As leader, the Merman captain provides additionaly physical stats to merman around him.",
    },
    "Ghostly Body": {
        "values": {"stats": StatBlock(secondary_health=(False, 10))},
        "class": RecoverHealth,
        "description": "Swirling energies surround and protect the Ghost, striken pierce its mist but never seem to connect.",
    },
    "Rivalries": {
        "values": {"stats": StatBlock(physical_attack=(True, 15), magical_attack=(True, 15))},
        "class": Rivalry,
        "description": "The Queen is a resentful person, those who have wronged her do not live long enough to regret it.",
    },
}
