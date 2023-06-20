from .battle import Enemy, StatBlock

POTENTIAL_ENEMIES = (
    Enemy(
        "Goblin",
        StatBlock(
            primary_health=(False, 5),
            physical_defense=(False, 2),
            physical_attack=(False, 3),
            tier=1
        ),
        None,
        None,
        "A simple goblin"
    ),
)