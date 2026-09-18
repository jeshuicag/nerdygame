from coin_ui import CoinUI

## 0 copper, 1 iron, 2 gold, 3 diamond (only available according to mechanic level)
## 0 player bag, 1 other bag, 2 trade area
def coinTrade(curr, amount, add, mechlevel):
    global ui
    ui = CoinUI(image_dir="coinimages")

    num_transfers = 0

    curr_bank = [0,[0, 0, 0, 0]]
    curr_bag = curr
    extras = [0,0,0,0]
    if add:
        extras = amount
    else:
        ui.showGoal(amount, mechlevel)

    while (add and (sum(extras) != 0 or sum(curr_bank[1])!=0)) or (not add and extras != amount):
        ## updateDisplayCoins should return selected coins, bank state when player tries to do transfer, destination, and if a trade is being attempted
        info = ui.updateDisplayCoins(curr_bag, extras, curr_bank, mechlevel)

        ## int representing coin type being asked for
        curr_bank[0] = info[1]

        ## check if the action is trade rather than transfer
        if info[3]:
            curr_bank[1] = tryTrade(curr_bank, mechlevel)
            continue

        ## format should be [[0, [5, 0, 0]]] (one type of coin), [[0, [5, 0, 1]], [1, [0, 2, 1]]] (two types of coin), etc.
        selected_coins = info[0]

        ## bag, extra bag, or bank
        destination = info[2]
        dest_amount = [0,0,0,0]
        match destination:
            case 0:
                dest_amount = curr_bag
            case 1:
                dest_amount = extras
            case 2:
                dest_amount = curr_bank[1]

        # figure out how much to add to destination
        move_amount = validSelected(selected_coins, destination)

        # figure out if destination can handle the load
        if not destCanAccomodate(move_amount, destination, dest_amount):
            continue

        # move the coins
        dest_amount = [x + y for x, y in zip(dest_amount, move_amount)]
        match destination:
            case 0:
                curr_bag = dest_amount
            case 1:
                extras = dest_amount
            case 2:
                curr_bank[1] = dest_amount

        # account for loss of coins from moved from locations
        for place in [0,1,2]:
            if place != destination:
                coinsToSubtract = coinsSelectedFromPlace(selected_coins, place)
                if place == 0:
                    curr_bag = [x - y for x, y in zip(curr_bag, coinsToSubtract)]
                if place == 1:
                    extras = [x - y for x, y in zip(extras, coinsToSubtract)]
                if place == 2:
                    curr_bank[1] = [x - y for x, y in zip(curr_bank[1], coinsToSubtract)]

        num_transfers += 1

    if sum(curr_bank[1]) > 0:
        curr_bag = [x + y for x, y in zip(curr_bag, curr_bank[1])]
        curr_bank[1] = [0,0,0,0]
        ui.bankToBag(curr_bag, curr_bank[1])
        
    ui.warn("You did it!")
    ui.close(2000)

    return curr_bag, num_transfers

## figure out how much of each coin type is actually moved
def validSelected(selected, dest):
    valid_select = [0,1,2]
    valid_select.remove(dest)

    select_return =[0,0,0,0]

    for coinType in selected:
        for loc in valid_select:
            select_return[coinType[0]] += coinType[1][loc]

    return select_return

## check if destination can handle amount of coins
def destCanAccomodate(influx, dest, curr_dest):
    if dest == 2 and sum(influx) + sum(curr_dest) > 10:
        ui.warn("The bank can only hold 10 coins at a time")
        return False
    elif dest == 1 or dest == 0:
        if not all(i < 10 for i in [x + y for x, y in zip(influx, curr_dest)]):
            ui.warn("This area can't hold that many coins")
            return False
    return True

## get how many selected coins are from specific location
def coinsSelectedFromPlace(selected_coins, dest):
    toreturn = [0,0,0,0]

    for cointype in selected_coins:
        toreturn[cointype[0]] = cointype[1][dest]

    return toreturn

def tryTrade(bank, level):
    temp_bank = bank[1]

    coinWanted = bank[0]
    if not coinWanted == 0:
        if temp_bank[coinWanted - 1] == 10:
            temp_bank[coinWanted - 1] = 0
            temp_bank[coinWanted] = 1
            ui.warn("trade successful!")
            return temp_bank
    if not coinWanted == level:
        if temp_bank[coinWanted + 1] == 1 and sum(temp_bank) == 1:
            temp_bank[coinWanted + 1] = 0
            temp_bank[coinWanted] = 10
            ui.warn("trade successful!")
            return temp_bank
    ui.warn("The trade center requires exact change")
    return temp_bank
            
## saved = coinTrade([0,1,0,0], [2,0,0,0], False, 1)

