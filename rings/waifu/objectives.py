from __future__ import annotations

import typing
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    from .battle import Battle
    from .entities import StattedEntity


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


class StandardObjective(Objective):
    name: str = "Elimination"
    victory_condition: str = "Kill all enemies"
    defeat_condition: str = "Do not lose all your troops."

    def is_defeat(self, battle: Battle) -> bool:
        return bool(battle.players)

    def is_victory(self, battle: Battle) -> bool:
        return bool(battle.enemies)


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
