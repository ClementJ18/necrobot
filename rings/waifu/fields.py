from collections import Counter

from .battle import Battlefield, Size

default_field = [
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1],
    [3, 1, 0, 0, 3, 1, 1, 0, 1, 1, 0, 0],
    [1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1],
    [0, 0, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1],
    [1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
]

POTENTIAL_FIELDS = (
    Battlefield(
        default_field,
        Size(len(default_field[0]), len(default_field)),
        name="Large Plain",
        description="A large plains with some holes",
        enemy_count=Counter(x for xs in default_field for x in xs)[3],
    ),
)
