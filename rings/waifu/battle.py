import enum
import random
from dataclasses import dataclass, field
from typing import Dict, List, Union

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

from .base import Coords, Size, get_symbol
from .entities import Character, Enemy


class InvalidPosition(Exception):
    pass


class Terrain:
    pass


class Event:
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
    tiles: List[List[TileType]]
    size: Size
    name: str
    description: str
    enemy_count: int
    grid: List[List[TileType]] = ()

    def initialise(self):
        # transform into a matrix for pathfinding
        self.grid = [[max(1, cell) for cell in row] for row in self.tiles]

    def walkable_grid(self, non_walkable: List = ()):
        return [
            [0 if cell < 1 or (x, y) in non_walkable else 1 for x, cell in enumerate(row)] 
            for y, row in enumerate(self.tiles)
        ]


class ActionType(enum.Enum):
    moved = "moved"
    attacked = "attacked"
    skill = "activated a skill"
    killed = "killed"
    died = "has fallen in battle"

    def __str__(self):
        return str(self.value)

@dataclass
class ActionEntry:
    character: Character
    action: ActionType
    arg: Union[Character, MovementType] = None

    def __str__(self):
        string = f"{self.character} {self.action.value}"
        if self.arg is not None:
            string += f" {self.arg}"

        return string

@dataclass
class Battle:
    _players: List[Character]
    _enemies: List[Enemy]
    # terrain: Terrain
    # event: Event
    battlefield: Battlefield
    used_last_turn: List[Character] = field(default_factory=list)
    action_log: List[str] = field(default_factory=list)

    @property
    def players(self):
        return [p for p in self._players if p.is_alive()]
    
    @property
    def enemies(self):
        return [e for e in self._enemies if e.is_alive()]

    def can_move_this_turn(self, char: Character) -> bool:
        return char not in self.used_last_turn

    def pick_enemies(self) -> List[Character]:
        valid_list = [enemy for enemy in self.enemies if enemy not in self.used_last_turn]
        return random.sample(valid_list, len(valid_list) // 3)
    
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

    def get_positions(self, value: TileType) ->List[Coords]:
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

    def initialise(self):
        player_positions = self.get_positions(TileType.player_start)
        for player, position in zip(self.players, player_positions):
            player.position = position

        enemy_positions = self.get_positions(TileType.enemy_start)
        for enemy, position in zip(self.enemies, enemy_positions):
            enemy.position = position

        self.battlefield.initialise()

        for index, character in enumerate(self.players + self.enemies):
            character.index = index

    def move_character(self, character: Character, *, new_position: Coords = (), change: Coords = ()):
        if not new_position and not change:
            raise ValueError("Specify either change or new_position")
        
        if change:
            new_position = (character.position[0] + change[0], character.position[1] + change[1])

        distance = get_distance(character.position, new_position)
        character.position = new_position
        character.current_movement_range -= distance
        self.action_log.append(f"{character} ({get_symbol(character.index)}) {ActionType.moved} {distance} meters")

    def attack_character(self, attacker: Character, attackee: Character):
        damage = attacker.attack(attackee)

        if attackee.is_alive():
            self.action_log.append(f"{attacker} ({get_symbol(attacker.index)}) {ActionType.attacked} {attackee} for {damage}")
        else:
            self.action_log.append(f"{attacker} ({get_symbol(attacker.index)}) {ActionType.killed} {attackee} with {damage}")

    def use_active_skill(self, character: Character):
        self.action_log.append(f"{get_symbol(character.index)} - {character} {ActionType.skill}")

    def do_ai_turn(self):
        for enemy in self.enemies:
            self.pick_ai_action(enemy)

    def pick_ai_action(self, character: Character):
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
        for end in ends:
            neighbors = grid.neighbors(end)
            for neighbor in neighbors:
                n = (neighbor.x, neighbor.y)
                if n in adjacent:
                    current_path = [n]
                    break

                path, _ = finder.find_path(start, neighbor, grid)
                if not path:
                    continue

                path.append(n)
                if len(path) < len(current_path) or not current_path:
                    current_path = path

        new_position = current_path[character.movement_range] if character.movement_range <= len(current_path) else current_path[-1]
        self.move_character(character, new_position=new_position)

        adjacent = self.get_adjacent_positions(character.position)
        targets = [player for player in self.players if player.position in adjacent.values()]

        if targets:
            return self.attack_character(character, random.choice(targets))
        
    def end_turn(self):
        for e in self.players + self.enemies:
            e.end_turn()
