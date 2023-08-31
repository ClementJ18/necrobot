from .base import StatBlock
from .entities import Enemy

Goblin = Enemy(
    name="Goblin",
    stats=StatBlock(
        primary_health=(False, 50),
        secondary_health=(False, 5),
        physical_defense=(False, 5),
        physical_attack=(False, 15),
        tier=1,
    ),
    description="A simple goblin",
)
