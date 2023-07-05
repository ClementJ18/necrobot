from collections import Counter
import enum
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Union

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

from .base import Coords, DamageInstance, Size, get_symbol
from .entities import Character, Enemy


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
    character: Character
    distance: int

    def eq(self, other: "MoveAction") -> bool:
        return self.character == other.character

    def __add__(self, other: "MoveAction") -> "MoveAction":
        return MoveAction(self.character, self.distance + other.distance)

    def __str__(self) -> str:
        return (
            f"{get_symbol(self.character.index)} - {self.character} moved {self.distance} meters"
        )


@dataclass(eq=False)
class AttackAction(ActionLog):
    character: Character
    damage: DamageInstance
    attackee: Character

    def eq(self, other: "AttackAction") -> bool:
        return self.character == other.character and self.attackee == other.attackee

    def __add__(self, other: "AttackAction") -> "AttackAction":
        return AttackAction(self.character, self.damage + other.damage, other.attackee)

    def __str__(self) -> str:
        return f"{get_symbol(self.character.index)} - {self.character} {'attacked' if self.attackee.is_alive() else 'killed'} {self.attackee} ({get_symbol(self.attackee.index)}) for {self.damage.amount} health"


@dataclass(eq=False)
class SkillAction(ActionLog):
    character: Character

    def eq(self, other: "SkillAction") -> bool:
        return False

    def __add__(self, other: object) -> object:
        return SkillAction(self.character)

    def __str__(self):
        return f"{get_symbol(self.character.index)} - {self.character} used {self.character.active_skill.name}"


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


def get_distance(origin: Coords, destination: Coords):
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    return abs(dx) + abs(dy)


@dataclass
class Battlefield:
    tiles: List[List[int]]
    name: str
    description: str
    grid: List[List[int]] = ()

    size: Size = Size(0, 0)
    enemy_count: int = 0

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

    def move_character(
        self, character: Character, *, new_position: Coords = (), change: Coords = ()
    ):
        if not new_position and not change:
            raise ValueError("Specify either change or new_position")

        if change:
            new_position = (character.position[0] + change[0], character.position[1] + change[1])

        distance = get_distance(character.position, new_position)
        character.position = new_position
        character.current_movement_range -= distance

        self.add_action_log(MoveAction(character, distance))

    def attack_character(self, attacker: Character, attackee: Character):
        if attacker.skill_is_active():
            attacker.active_skill.on_attack(self, attacker, attackee)

        if attackee.skill_is_active():
            attackee.active_skill.on_defend(self, attackee, attacker)

        damage = attacker.attack(attackee)
        attacker.has_attacked = True

        self.add_action_log(AttackAction(attacker, damage, attackee))

    def use_active_skill(self, character: Character):
        character.active_skill.on_activation(self, character)

        self.add_action_log(SkillAction(character))
        character.active_skill.was_activated = True

    def pick_ai_action(self, character: Character):
        logging.info("Pathfinding %s at %s", character.name, character.position)
        adjacent = self.get_adjacent_positions(character.position)
        targets = [player for player in self.players if player.position in adjacent.values()]

        if targets:
            return self.attack_character(character, random.choice(targets))

        entities = self.players + self.enemies
        grid = Grid(matrix=self.battlefield.walkable_grid([x.position for x in entities]))

        start = grid.node(*character.position)
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
            current_path[character.movement_range]
            if character.movement_range <= len(current_path)
            else current_path[-1]
        )
        self.move_character(character, new_position=new_position)

        adjacent = self.get_adjacent_positions(character.position)
        targets = [player for player in self.players if player.position in adjacent.values()]

        if targets:
            return self.attack_character(character, random.choice(targets))

    def end_turn(self):
        for e in self.players + self.enemies:
            e.end_turn()
