from .entities import Enemy, StatBlock

POTENTIAL_ENEMIES = (
    Enemy(
        name="Goblin",
        stats=StatBlock(
            primary_health=(False, 5),
            physical_defense=(False, 2),
            physical_attack=(False, 3),
            tier=1
        ),
        description="A simple goblin"
    ),
)