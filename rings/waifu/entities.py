from dataclasses import dataclass, field
from typing import List

from .base import Coords, DataClass, StatBlock, DamageInstance
from .skills import Modifier, PassiveSkill, ActiveSkill


@dataclass(kw_only=True)
class StattedEntity(DataClass):
    name: str
    stats: StatBlock
    active_skill: ActiveSkill = None
    passive_skill: PassiveSkill = None

    movement_range: int = 3
    current_movement_range: int = 0
    index: int = 0

    has_used_active_skill: bool = False
    has_attacked: bool = False
    modifiers: List[Modifier] = field(default_factory=list)
    position: Coords = None

    def __str__(self):
        return self.name

    def __post_init__(self):
        self.stats.current_primary_health = self.calculate_stat("primary_health")
        self.stats.max_primary_health = self.stats.current_primary_health

        self.stats.current_secondary_health = self.calculate_stat("secondary_health")
        self.stats.max_secondary_health = self.stats.current_secondary_health

        self.current_movement_range = self.movement_range

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

    def calculate_damage(self, attack, defense) -> DamageInstance:
        return max(1, attack - defense)

    def is_alive(self):
        return self.stats.is_alive()

    def attack(self, attackee: "StattedEntity"):
        if self.is_physical:
            attack = self.calculate_physical_attack()
            defense = self.calculate_physical_defense()
        else:
            attack = self.calculate_magical_attack()
            defense = self.calculate_magical_defense()

        attack_buff = 0
        if self.skill_is_active():
            attack_buff += self.active_skill.on_calculate_attack(
                self, attackee, attack, self.is_physical
            )

        if self.has_passive():
            attack_buff += self.passive_skill.on_calculate_attack(
                self, attackee, attack, self.is_physical
            )

        for modifier in self.modifiers:
            attack_buff += modifier.on_calculate_attack(self, attackee, attack, self.is_physical)

        defense_buff = 0
        if attackee.skill_is_active():
            defense_buff += attackee.active_skill.on_calculate_defense(
                attackee, self, defense, self.is_physical
            )

        if attackee.has_passive():
            defense_buff += attackee.passive_skill.on_calculate_defense(
                attackee, self, defense, self.is_physical
            )

        for modifier in attackee.modifiers:
            defense_buff += modifier.on_calculate_defense(self, attackee, attack, self.is_physical)

        damage = DamageInstance(
            self.calculate_damage(attack + attack_buff, defense + defense_buff),
            True,
        )

        if self.skill_is_active():
            damage = self.active_skill.on_deal_damage(self, attackee, damage)

        if self.has_passive():
            damage = self.passive_skill.on_deal_damage(self, attackee, damage)

        for modifier in self.modifiers:
            damage = modifier.on_deal_damage(self, attackee, damage)

        if attackee.skill_is_active():
            damage = attackee.active_skill.on_take_damage(attackee, self, damage)

        if attackee.has_passive():
            damage = attackee.passive_skill.on_take_damage(attackee, self, damage)

        for modifier in attackee.modifiers:
            damage = modifier.on_take_damage(attackee, self, damage)

        damage.finalise()

        attackee.take_damage(damage.amount, damage.secondary)
        return damage

    def take_damage(self, amount: int, secondary: bool = True):
        if secondary:
            if self.stats.current_secondary_health > amount:
                self.stats.current_secondary_health -= amount
                return

            amount -= self.stats.current_secondary_health
            self.stats.current_secondary_health = 0

        if self.stats.current_primary_health > amount:
            self.stats.current_primary_health -= amount
            return

        self.stats.current_primary_health = 0

    def grant_health(self, amount: int, *, secondary: bool = False, respect_max: bool = True):
        key = "secondary" if secondary else "primary"
        current_health = f"current_{key}_health"
        max_health = f"max_{key}_health"

        to_add = amount
        if respect_max:
            to_add = min(
                amount,
                max(0, getattr(self.stats, max_health) - getattr(self.stats, current_health)),
            )

        setattr(self.stats, current_health, getattr(self.stats, current_health) + to_add)

    def end_turn(self):
        self.current_movement_range = self.movement_range

        self.has_attacked = False

        if self.active_skill is not None:
            self.active_skill.end_turn()

        self.modifiers = [modifier for modifier in self.modifiers if not modifier.end_turn()]

    def can_use_skill(self):
        if self.active_skill is None:
            return False

        return self.active_skill.can_activate()

    def skill_is_active(self):
        if self.active_skill is None:
            return False

        return self.active_skill.is_active()
    
    def has_passive(self):
        return self.passive_skill is not None
    
    def add_modifier(self, modifier: Modifier):
        existing_modifier = next((mod for mod in self.modifiers if mod == modifier), None)
        if existing_modifier is None or modifier.can_duplicate:
            self.modifiers.append(modifier)
        elif modifier.can_stack:
            existing_modifier.duration += modifier.duration
        else:
            existing_modifier.duration = max(existing_modifier.duration, modifier.duration)

@dataclass
class Character(StattedEntity):
    weapon: StattedEntity = None
    artefact: StattedEntity = None

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
class Enemy(StattedEntity):
    description: str = None
