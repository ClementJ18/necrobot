from collections import Counter

from .battle import Battlefield, Size

# 0 : non-walkable
# 1 : walkable
# 2 : player placements
# 3 : enemy placements

default_field = (
    (0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1),
    (0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1),
    (3, 1, 0, 0, 3, 1, 1, 0, 1, 1, 0, 0),
    (1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1),
    (0, 0, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1),
    (1, 1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 2),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0),
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0),
)

test_field = (
    (1, 1, 1, 1, 1),
    (1, 3, 1, 3, 1),
    (1, 1, 1, 1, 1),
    (2, 1, 2, 1, 2),
)

POTENTIAL_FIELDS = (
    Battlefield(
        tiles=default_field,
        name="Large Plain",
        description="A large plains with some holes",
    ),
    Battlefield(tiles=test_field, name="Debug Time", description="How'd you get here?"),
)
