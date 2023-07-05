from dataclasses import dataclass

from .base import Coords, DataClass, StatBlock, DamageInstance
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
    has_attacked: bool = False

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

    def attack(self, attackee: "StatedEntity"):
        if self.is_physical:
            attack = self.calculate_physical_attack()
            defense = self.calculate_physical_defense()
        else:
            attack = self.calculate_magical_attack()
            defense = self.calculate_magical_defense()

        if self.skill_is_active():
            attack += self.active_skill.on_calculate_attack(
                self, attackee, attack, self.is_physical
            )

        if attackee.skill_is_active():
            defense += self.active_skill.on_calculate_defense(
                attackee, self, defense, self.is_physical
            )

        damage = DamageInstance(
            self.calculate_damage(attack, defense),
            False,
        )

        if self.skill_is_active():
            damage = self.active_skill.on_deal_damage(self, attackee, damage)

        if attackee.skill_is_active():
            damage = attackee.active_skill.on_take_damage(attackee, self, damage)

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

    def can_use_skill(self):
        if self.active_skill is None:
            return False

        return self.active_skill.can_activate()

    def skill_is_active(self):
        if self.active_skill is None:
            return False

        return self.active_skill.is_active()


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
