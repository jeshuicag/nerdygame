
import cointrade
from enum import Enum

class Coin(Enum):
    COPPER = 0
    IRON = 1
    GOLD = 2
    DIAMOND = 3

class Task(Enum):
    GROCERY = 0
    SNAKE = 1
    COIN = 2
    PARTY = 3
    COUNTER = 4


## track where players are in each mechanic
mech_levels = []

## initialize levels
mechs[Task.GROCERY] = 0
mechs[Task.SNAKE] = 0
mechs[Task.COIN] = 0
mechs[Task.PARTY] = -1
mechs[Task.COUNTER] = -1

## track money
int coins[4] = [0, 0, 0, 0]

coins[Coin.COPPER] = 0
coins[Coin.IRON] = 0
coins[Coin.GOLD] = 0
coins[Coin.DIAMOND] = 0

taskqueue = ["grocshop", "snakehunt"]