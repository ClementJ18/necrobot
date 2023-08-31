from __future__ import annotations

import logging
import random
import typing
from dataclasses import dataclass

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

if typing.TYPE_CHECKING:
    from .battle import Battle
    from .entities import StattedEntity

logger = logging.getLogger()


class Objective:
    name: str
    victory_condition: str
    defeat_condition: str

    def is_defeat(self, battle: Battle) -> bool:
        raise NotImplementedError

    def is_victory(self, battle: Battle) -> bool:
        raise NotImplementedError

    def get_condition(self, battle: Battle, victory: bool):
        if victory:
            return self.victory_condition

        return self.defeat_condition

    def take_ai_action(self, battle: Battle, entity: StattedEntity):
        raise NotImplementedError


class StandardObjective(Objective):
    name: str = "Elimination"
    victory_condition: str = "Kill all enemies"
    defeat_condition: str = "Do not lose all your troops."

    def is_defeat(self, battle: Battle) -> bool:
        return not bool(battle.players)

    def is_victory(self, battle: Battle) -> bool:
        return not bool(battle.enemies)

    def take_ai_action(self, battle: Battle, entity: StattedEntity):
        logger.info("Pathfinding %s at %s", entity.name, entity.position)
        adjacent = battle.get_adjacent_positions(entity.position)
        targets = [player for player in battle.players if player.position in adjacent.values()]

        if targets:
            return battle.attack_entity(entity, random.choice(targets))

        entities = battle.players + battle.enemies
        grid = Grid(matrix=battle.battlefield.walkable_grid([x.position for x in entities]))

        start = grid.node(*entity.position)
        ends = [grid.node(*x.position) for x in battle.players]
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)

        current_path = []
        neighbors = {neighbor for end in ends for neighbor in grid.neighbors(end)}
        for neighbor in neighbors:
            n = (neighbor.x, neighbor.y)
            logger.info("Evaluating neighbor %s", n)
            if n in adjacent:
                logger.info("neighbor %s is adjacent %s", n, adjacent)
                current_path = [n]
                break

            grid.cleanup()
            path, _ = finder.find_path(start, neighbor, grid)
            if not path:
                logger.info("could not find path to %s", n)
                continue

            path.append(n)
            if len(path) < len(current_path) or not current_path:
                logger.info("path %s is better than old path %s", path, current_path)
                current_path = path
            else:
                logger.info("path %s is worse than old path %s", path, current_path)

        new_position = (
            current_path[entity.movement_range]
            if len(current_path) > entity.movement_range
            else current_path[-1]
            if entity.movement_range <= len(current_path)
            else current_path[-1]
        )
        battle.move_entity(entity, new_position=new_position)

        adjacent = battle.get_adjacent_positions(entity.position)
        targets = [player for player in battle.players if player.position in adjacent.values()]

        if targets:
            return battle.attack_entity(entity, random.choice(targets))


@dataclass
class KillBoss(StandardObjective):
    boss_index: int

    name: str = "Assassination"
    victory_condition: str = "Kill the {enemy} ({enemy.index})"

    def is_victory(self, battle: Battle) -> bool:
        return not battle._enemies[self.boss_index].is_alive()

    def get_condition(self, battle: Battle, victory: bool):
        args = {"enemy": battle._enemies[self.boss_index]}

        if victory:
            return self.victory_condition.format(**args)

        return self.defeat_condition
