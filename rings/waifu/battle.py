from __future__ import annotations

import enum
import logging
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

from .base import Coords, DamageInstance, Size, get_distance, get_symbol
from .entities import Character, Enemy, StattedEntity
from .objectives import Objective, StandardObjective

if TYPE_CHECKING:
    from .battle import Battle


class ActionLog:
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return self.eq(other)

    def eq(self, other: object) -> bool:
        raise NotImplementedError

    def __add__(self, other: object) -> object:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError


@dataclass(eq=False)
class MoveAction(ActionLog):
    entity: StattedEntity
    distance: int

    def eq(self, other: "MoveAction") -> bool:
        return self.entity == other.entity

    def __add__(self, other: "MoveAction") -> "MoveAction":
        return MoveAction(self.entity, self.distance + other.distance)

    def __str__(self) -> str:
        return f"{get_symbol(self.entity.index)} - {self.entity} moved {self.distance} meters"


@dataclass(eq=False)
class AttackAction(ActionLog):
    attacker: StattedEntity
    damage: DamageInstance
    attackee: StattedEntity

    def eq(self, other: "AttackAction") -> bool:
        return self.attacker == other.attacker and self.attackee == other.attackee

    def __add__(self, other: "AttackAction") -> "AttackAction":
        return AttackAction(self.attacker, self.damage + other.damage, other.attackee)

    def __str__(self) -> str:
        return f"{get_symbol(self.attacker.index)} - {self.attacker} {'attacked' if self.attackee.is_alive() else 'killed'} {self.attackee} ({get_symbol(self.attackee.index)}) for {self.damage.amount} health"


@dataclass(eq=False)
class SkillAction(ActionLog):
    entity: StattedEntity

    def eq(self, other: "SkillAction") -> bool:
        return False

    def __add__(self, other: object) -> object:
        return SkillAction(self.entity)

    def __str__(self):
        return (
            f"{get_symbol(self.entity.index)} - {self.entity} used {self.entity.active_skill.name}"
        )


class InvalidPosition(Exception):
    pass


class MovementType(enum.Enum):
    up = (0, -1)
    down = (0, 1)
    left = (-1, 0)
    right = (1, 0)

    def __str__(self):
        return self.name


class TileType(enum.Enum):
    wall = 0
    walkable = 1
    player_start = 2
    enemy_start = 3


def is_wakable(tile_type: Union[TileType, int]):
    if isinstance(tile_type, TileType):
        tile_type = tile_type.value

    return tile_type > 0


class BattleOverException(Exception):
    def __init__(self, victory: bool) -> None:
        self.victory = victory


@dataclass
class Battlefield:
    tiles: List[List[int]]
    name: str
    description: str
    grid: List[List[int]] = ()
    objective: Objective = StandardObjective()

    size: Size = Size(0, 0)
    enemy_count: int = 0

    enemies: List[StattedEntity] = ()

    def __post_init__(self):
        self.size = Size(len(self.tiles[0]), len(self.tiles))
        self.enemy_count = Counter(x for xs in self.tiles for x in xs)[3]

    def initialise(self):
        # transform into a matrix for pathfinding
        self.grid = [[max(1, cell) for cell in row] for row in self.tiles]

    def walkable_grid(self, non_walkable: List = ()):
        return [
            [0 if cell < 1 or (x, y) in non_walkable else 1 for x, cell in enumerate(row)]
            for y, row in enumerate(self.tiles)
        ]

    def check_victory(self, battle: Battle):
        if self.objective.is_victory(battle):
            raise BattleOverException(True)

        if self.objective.is_defeat(battle):
            raise BattleOverException(False)


@dataclass
class RandomBattlefield(Battlefield):
    """The random in random battlefield is for the randomized enemies."""

    weighted_choices: List[Tuple(int, StattedEntity)] = ()


@dataclass
class SetBattlefield(Battlefield):
    ordered_enemies: List[StattedEntity] = ()


@dataclass
class Battle:
    _players: List[Character]
    _enemies: List[Enemy]
    battlefield: Battlefield
    action_logs: List[ActionLog] = field(default_factory=list)

    @property
    def players(self):
        return [p for p in self._players if p.is_alive()]

    @property
    def enemies(self):
        return [e for e in self._enemies if e.is_alive()]

    def is_in_board(self, position: Coords) -> bool:
        if not 0 <= position[1] < self.battlefield.size.height:
            raise InvalidPosition("Y coordinate out of range")

        if not 0 <= position[0] < self.battlefield.size.length:
            raise InvalidPosition("X coordinate out of range")

        return True

    def _is_valid_movement(self, position: Coords, change: Coords, move_range: int) -> bool:
        new_pos = (position[0] + change[0], position[1] + change[1])
        self.is_in_board(new_pos)
        if not self.battlefield.tiles[new_pos[1]][new_pos[0]] > 0:
            raise InvalidPosition("Cannot move there")

        if any(e.position == new_pos for e in self.players + self.enemies):
            raise InvalidPosition("Somebody is already there")

        if get_distance(position, new_pos) > move_range:
            raise InvalidPosition("Not enough movement range.")

        return True

    def is_valid_movement(self, position: Coords, change: Coords, move_range: int) -> bool:
        try:
            return self._is_valid_movement(position, change, move_range)
        except InvalidPosition:
            return False

    def get_positions(self, value: TileType) -> List[Coords]:
        positions = []
        for y, row in enumerate(self.battlefield.tiles):
            if value.value not in row:
                continue

            for x, cell in enumerate(row):
                if cell == value.value:
                    positions.append((x, y))

        return positions

    def get_adjacent_positions(self, position: Coords) -> Dict[MovementType, Coords]:
        adjacents = {}

        for move in MovementType:
            new_pos = (position[0] + move.value[0], position[1] + move.value[1])
            try:
                self.is_in_board(new_pos)
                adjacents[move] = new_pos
            except InvalidPosition:
                pass

        return adjacents

    def add_action_log(self, log: ActionLog):
        if not self.action_logs:
            self.action_logs.append(log)
        elif self.action_logs[-1] == log:
            self.action_logs[-1] = self.action_logs[-1] + log
        else:
            self.action_logs.append(log)

    def initialise(self):
        player_count = len(self.players)
        enemy_count = len(self.enemies)

        player_positions = self.get_positions(TileType.player_start)
        for player, position, index in zip(self.players, player_positions, range(player_count)):
            player.position = position
            player.index = index

        enemy_positions = self.get_positions(TileType.enemy_start)
        for enemy, position, index in zip(
            self.enemies, enemy_positions, range(player_count, player_count + enemy_count)
        ):
            enemy.position = position
            enemy.index = index

        self.battlefield.initialise()

    def move_entity(
        self, entity: StattedEntity, *, new_position: Coords = (), change: Coords = ()
    ):
        if not new_position and not change:
            raise ValueError("Specify either change or new_position")

        if change:
            new_position = (entity.position[0] + change[0], entity.position[1] + change[1])

        distance = get_distance(entity.position, new_position)
        entity.position = new_position
        entity.current_movement_range -= distance

        self.add_action_log(MoveAction(entity, distance))

    def attack_entity(self, attacker: StattedEntity, attackee: StattedEntity):
        if attacker.skill_is_active():
            attacker.active_skill.on_attack(self, attacker, attackee)

        if attacker.has_passive():
            attacker.passive_skill.on_attack(self, attacker, attackee)

        for modifier in attacker.modifiers:
            modifier.on_attack(self, attacker, attackee)

        if attackee.skill_is_active():
            attackee.active_skill.on_defend(self, attackee, attacker)

        if attackee.has_passive():
            attackee.passive_skill.on_defend(self, attackee, attacker)

        for modifier in attackee.modifiers:
            modifier.on_defend(self, attackee, attacker)

        damage = attacker.attack(attackee)
        attacker.has_attacked = True

        self.add_action_log(AttackAction(attacker, damage, attackee))

    def use_active_skill(self, entity: StattedEntity):
        entity.active_skill.on_activation(self, entity)

        if entity.has_passive():
            entity.passive_skill.on_activation(self, entity)

        for modifier in entity.modifiers:
            modifier.on_activation(self, entity)

        self.add_action_log(SkillAction(entity))
        entity.active_skill.was_activated = True

    def pick_ai_action(self, entity: StattedEntity):
        logging.info("Pathfinding %s at %s", entity.name, entity.position)
        adjacent = self.get_adjacent_positions(entity.position)
        targets = [player for player in self.players if player.position in adjacent.values()]

        if targets:
            return self.attack_entity(entity, random.choice(targets))

        entities = self.players + self.enemies
        grid = Grid(matrix=self.battlefield.walkable_grid([x.position for x in entities]))

        start = grid.node(*entity.position)
        ends = [grid.node(*x.position) for x in self.players]
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)

        current_path = []
        neighbors = {neighbor for end in ends for neighbor in grid.neighbors(end)}
        for neighbor in neighbors:
            n = (neighbor.x, neighbor.y)
            logging.info("Evaluating neighbor %s", n)
            if n in adjacent:
                logging.info("neighbor %s is adjacent %s", n, adjacent)
                current_path = [n]
                break

            grid.cleanup()
            path, _ = finder.find_path(start, neighbor, grid)
            if not path:
                logging.info("could not find path to %s", n)
                continue

            path.append(n)
            if len(path) < len(current_path) or not current_path:
                logging.info("path %s is better than old path %s", path, current_path)
                current_path = path
            else:
                logging.info("path %s is worse than old path %s", path, current_path)

        new_position = (
            current_path[entity.movement_range]
            if len(current_path) > entity.movement_range
            else current_path[-1]
            if entity.movement_range <= len(current_path)
            else current_path[-1]
        )
        self.move_entity(entity, new_position=new_position)

        adjacent = self.get_adjacent_positions(entity.position)
        targets = [player for player in self.players if player.position in adjacent.values()]

        if targets:
            return self.attack_entity(entity, random.choice(targets))

    def end_turn(self):
        for e in self.players + self.enemies:
            if e.skill_is_active():
                e.active_skill.on_end_turn(self, e)

            if e.has_passive():
                e.passive_skill.on_end_turn(self, e)

            for modifier in e.modifiers:
                modifier.on_end_turn(self, e)

            e.end_turn()

    def start_turn(self):
        for e in self.players + self.enemies:
            if e.skill_is_active():
                e.active_skill.on_start_turn(self, e)

            if e.has_passive():
                e.passive_skill.on_start_turn(self, e)

            for modifier in e.modifiers:
                modifier.on_start_turn(self, e)
