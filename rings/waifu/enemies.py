from .entities import Enemy
from .base import StatBlock

POTENTIAL_ENEMIES = (
    Enemy(
        name="Goblin",
        stats=StatBlock(
            primary_health=(False, 15),
            physical_defense=(False, 2),
            physical_attack=(False, 3),
            tier=1,
        ),
        description="A simple goblin",
    ),
)
