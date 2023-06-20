import copy
import enum
import inspect
import random
from collections import namedtuple
from dataclasses import dataclass, field, fields
from typing import Dict, List, Tuple, Union

Coords = Tuple[int, int] # (x, y)
Size = namedtuple("Size", "length height")

POSITION_EMOJIS = [":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:",]


class InvalidPosition(Exception):
    pass


class PassiveSkillType(enum.Enum):
    pass


class ActiveSkillType(enum.Enum):
    pass


class DataClass:
    @classmethod
    def from_dict(cls, env):      
        return cls(**{
            k: v for k, v in env.items() 
            if k in inspect.signature(cls).parameters
        })

@dataclass
class Stat:
    is_percent: bool
    stat: float

    @property
    def modifier(self):
        if not self.is_percent:
            return 0
        
        return self.stat
    
    @property
    def raw(self):
        if self.is_percent:
            return 0
        
        return self.stat
        

@dataclass
class StatBlock(DataClass):
    primary_health: Stat
    secondary_health: Stat = (False, 0)
    physical_defense: Stat = (False, 0)
    physical_attack: Stat = (False, 0)
    magical_defense: Stat = (False, 0)
    magical_attack: Stat = (False, 0)

    tier: int = 0

    current_primary_health: int = 0
    current_secondary_health: int = 0
    max_primary_health: int = 0
    max_secondary_health: int = 0

    @property
    def tier_modifier(self):
        return 0.02 * self.tier

    def is_alive(self):
        return self.current_primary_health > 0 or self.current_secondary_health > 0

    def __post_init__(self):
        for field in fields(self):
            if not field.type is Stat:
                continue

            value = getattr(self, field.name)
            if not isinstance(value, field.type):
                setattr(self, field.name, field.type(*value))

    def calculate_raw(self, stat_name):
        stat: Stat = getattr(self, stat_name)
        if stat is None:
            raise AttributeError(f"{stat_name} not a valid stat")
        
        return stat.raw
    
    def calculate_modifier(self, stat_name):
        stat: Stat = getattr(self, stat_name)
        if stat is None:
            raise AttributeError(f"{stat_name} not a valid stat")
        
        return stat.modifier

@dataclass
class StatedEntity(DataClass):
    name: str
    stats: StatBlock
    active_skill: ActiveSkillType = None
    passive_skill: PassiveSkillType = None

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
    
    def calculate_damage(self, attack, defense):
        return max(1, attack-defense)

    def is_alive(self):
        return self.stats.is_alive()
    
    def attack(self, attackee: 'StatedEntity'):
        if self.is_physical:
            damage = self.calculate_damage(self.calculate_physical_attack(), attackee.calculate_physical_defense())
        else:
            damage = self.calculate_damage(self.calculate_magical_attack(), attackee.calculate_magical_defense())

        attackee.take_damage(damage)

        return damage

    def take_damage(self, damage):
        self.stats.current_secondary_health -= damage

        if self.stats.current_secondary_health < 0:
            self.stats.current_primary_health += self.stats.current_secondary_health
            self.stats.current_secondary_health = 0

        if self.stats.current_primary_health < 0:
            self.stats.current_primary_health = 0

    def __str__(self):
        return self.name
    
    def __post_init__(self):
        self.stats.current_primary_health = self.calculate_stat("primary_health")
        self.stats.max_primary_health = self.stats.current_primary_health
        
        self.stats.current_secondary_health = self.calculate_stat("secondary_health")
        self.stats.max_secondary_health = self.stats.current_secondary_health


@dataclass
class Character(StatedEntity):
    weapon: "Character" = None
    artefact: "Character" = None

    position: Coords = None

    @property
    def is_physical(self):
        return self.weapon.stats.calculate_raw("physical_attack") > 0
    
    def calculate_stat(self, stat_name):
        base = 0
        modifier = self.stats.tier_modifier

        for source in (self, self.weapon, self.artefact):
            base += source.stats.calculate_raw(stat_name)
            modifier += source.stats.calculate_modifier(stat_name)

        return int(base + (base * modifier))
    
    def __post_init__(self):
        self.stats.current_primary_health = self.calculate_stat("primary_health")
        self.stats.max_primary_health = self.stats.current_primary_health
        
        self.stats.current_secondary_health = self.calculate_stat("secondary_health")
        self.stats.max_secondary_health = self.stats.current_secondary_health
    

@dataclass
class Enemy(StatedEntity):
    description: str = None
    position: Coords = None


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

    def walkable_grid(self, include_entities=False):
        pass

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
    _enemies: List[Character]
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

    def _is_valid_movement(self, position: Coords, change: Coords) -> bool:
        new_pos = (position[0] + change[0], position[1] + change[1])
        self.is_in_board(new_pos)
        if not self.battlefield.tiles[new_pos[1]][new_pos[0]] > 0:
            raise InvalidPosition("Cannot move there")
        
        if any(e.position == new_pos for e in self.players + self.enemies):
            raise InvalidPosition("Somebody is already there")
        
        return True
    
    def is_valid_movement(self, position: Coords, change: Coords) -> bool:
        try:
            return self._is_valid_movement(position, change)
        except InvalidPosition:
            return False
    
    def move_character(self, character: Character, movements: List[MovementType]) -> Coords:
        for movement in movements:
            try:
                self.is_valid_movement(character.position, movement.value)
            except InvalidPosition:
                return
            
            yield (character.position[0] + movement.value[0], character.position[1] + movement.value[1])

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

    def move_character(self, character: Character, direction: MovementType):
        character.position = (character.position[0] + direction.value[0], character.position[1] + direction.value[1])
        self.action_log.append(f"{character} {ActionType.moved} {direction}")

    def attack_character(self, attacker: Character, attackee: Character):
        damage = attacker.attack(attackee)

        if attackee.is_alive():
            self.action_log.append(f"{attacker} {ActionType.attacked} {attackee} for {damage}")
        else:
            self.action_log.append(f"{attacker} {ActionType.killed} {attackee} with {damage}")

    def use_active_skill(self, character: Character):
        self.action_log.append(f"{character} {ActionType.skill}")

    def do_turn_move(self, character: Character, direction: MovementType):
        self.move_character(character, direction)
        self.do_ai_turn()

    def do_ai_turn(self):
        potential_enemies = [enemy for enemy in self.enemies if enemy not in self.used_last_turn]

        missing_enemies = len(potential_enemies) - self.battlefield.enemy_count // 0.33
        if missing_enemies > 0:
            potential_enemies.extend(random.sample([enemy for enemy in self.enemies if enemy not in potential_enemies], missing_enemies))

        enemies = random.sample(potential_enemies, self.battlefield.enemy_count // 0.33)

    def pick_ai_action(self, character: Character):
        adjacent = self.get_adjacent_positions(character.position)
        targets = [player for player in self.players if player.position in adjacent.values()]

        if targets:
            return self.attack_character(character, random.choice(targets))
        
        

            



