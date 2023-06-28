from collections import namedtuple
from typing import Tuple

Coords = Tuple[int, int] # (x, y)
Size = namedtuple("Size", "length height")

POSITION_EMOJIS = [":zero:", ":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:"]

def get_symbol(index):
    return f"{index}\ufe0f\N{COMBINING ENCLOSING KEYCAP}"
