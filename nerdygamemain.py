
import cointrade

## track where players are in each mechanic
mech_levels = {}

## initialize levels
mechs["grocshop"] = 0
mechs["snakehunt"] = 0
mechs["cashier"] = -1
mechs["party"] = -1
mechs["pizza"] = -1

## track money
coins = {}

coins["copper"] = 0
coins["iron"] = 0
coins["gold"] = 0
coins["diamond"] = 0

taskqueue = ["grocshop", "snakehunt"]