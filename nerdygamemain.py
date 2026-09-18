import grocshop
import cointrade
import snakehunt
import bdayparty
import bySlice

import random

from mainarea_ui import MainUI

from enum import IntEnum

class Coin(IntEnum):
    COPPER = 0
    IRON = 1
    GOLD = 2
    DIAMOND = 3

class Task(IntEnum):
    GROCERY = 0
    SNAKE = 1
    COIN = 2
    PARTY = 3
    COUNTER = 4

def runShop():

    ## track where players are in each mechanic
    global mechs 
    mechs = [None] * 5

    ## initialize levels
    mechs[Task.GROCERY] = [0, 3, 60] #level, num ingredients, time limit
    mechs[Task.SNAKE] = [0, 0, 90, 3] #catch tail level, catch head level, time limit, snake limit
    mechs[Task.COIN] = 0 #level
    mechs[Task.PARTY] = -1 #locked, start at 2 when playable, level represents max kids
    mechs[Task.COUNTER] = [-1, 2, 60] #doubles, num_rounds, time_limit

    ## track money
    global coins 
    coins = [0, 0, 0, 0]

    coins[Coin.COPPER] = 9
    coins[Coin.IRON] = 0
    coins[Coin.GOLD] = 0
    coins[Coin.DIAMOND] = 0

    taskqueue = ["grocshop", "cointradem", "snakehunt", "cointradep"]

    global ui
    ui = MainUI(image_dir="mainimages")
    ui.updateTasks(taskqueue)
    ui.updateCoins(coins, mechs[Task.COIN])

    ui.note("This pizza shop is now yours-- stock it, run it, and make money!", 0)

    while taskqueue:
        ui.updateTasks(taskqueue)
        ui.updateCoins(coins, mechs[Task.COIN])
        match taskqueue.pop(0):
            case "grocshop":
                ## 0 for 'let's go!' or play button, 1 for 'hire someone' button, which switch the text to '+1 employee'
                ui.note("We need ingredients! I drew up a list for you-- let's go grocery shopping!", 0)

                ## two levels-- 0 and 1. 0 is player goes shopping. 1 is mastery achieved, grocery shopper hired.
                level = mechs[Task.GROCERY][0]

                curr_total_goal = mechs[Task.GROCERY][1]
                curr_time_goal = mechs[Task.GROCERY][2]

                if level == 0:
                    ui.close()
                    total_completed, final_time, mistakes = grocshop.go_shopping(curr_total_goal, curr_time_goal)
                    ui = MainUI(image_dir="mainimages")

                    mechs[Task.GROCERY][1], mechs[Task.GROCERY][2] = updateGroceryStats(curr_total_goal, curr_time_goal, total_completed, final_time, mistakes, taskqueue)
                    taskqueue.append("grocshop")
                    taskqueue.append("cointradem")

                elif level == 1:
                    ui.note("Hm... its a shame to waste your time on grocery shopping. Let's hire someone! You won't have to shop anymore, but if the new hire asks for your help, please help them!", 1)
            
            case "snakehunt":
                ui.note("Time to hunt our special ingredient! Pepperoni snakes-- take Buddy with you. While you catch the snake's tail, he can catch the snake's head.", 0)

                curr_level_tail = mechs[Task.SNAKE][0]
                curr_level_head = mechs[Task.SNAKE][1]
                start_point = random.randint(1,120)

                if curr_level_tail == 0:
                    start_point = 1

                curr_time_goal = mechs[Task.SNAKE][2]
                curr_snake_goal = mechs[Task.SNAKE][3]

                if curr_level_head == 0:
                    ui.close()
                    t_attempts, h_attempts, snakes_caught, final_time = snakehunt.catchSnake(start_point, curr_time_goal, curr_snake_goal)
                    ui = MainUI(image_dir="mainimages")
                    
                    mechs[Task.SNAKE][0], mechs[Task.SNAKE][1], mechs[Task.SNAKE][2], mechs[Task.SNAKE][3] = updateSnakeStats(curr_level_tail, curr_time_goal, curr_snake_goal, t_attempts, h_attempts, snakes_caught, final_time)
                    taskqueue.append("snakehunt")
                    if mechs[Task.PARTY] == -1:
                        taskqueue.append("cointradep")

                elif curr_level_head == 1:
                    ui.note("Hm... its a shame to waste your time on snake hunting. Let's hire someone! You won't have to hunt anymore, but if the new hire asks for your help, please help them!", 1)

            case "cointradem":
                minusamount = [0,0,0,0]
                mechlevel = mechs[Task.COIN]
                for i in range(mechlevel + 1):
                    minusamount[i] = random.randint(1, coins[i]//2)

                if arrToNum(coins) < arrToNum(minusamount):
                    minusamount = max(1, arrToNum(coins) - 2)

                if mechs[Task.GROCERY][0] == 0:
                    ui.note(f"We have to pay for groceries! Put {arrToNum(minusamount)} in the extras bag.", 0)
                else:
                    ui.note(f"The shopper needs money groceries! Put {arrToNum(minusamount)} in the extras bag for them.", 0)

                ui.close()
                coins, trades = cointrade.coinTrade(coins, minusamount, False, mechlevel)
                ui = MainUI(image_dir="mainimages")
                
                mechs[Task.COIN] = upgradeCoins(trades)

            case "cointradep":
                addamount = [0,0,0,0]
                mechlevel = mechs[Task.COIN]
                for i in range(mechlevel + 1):
                    addamount[i] = random.randint(0, coins[i]//2)

                while arrToNum(coins) + arrToNum(addamount) > 10**(mechlevel + 1):
                    addamount = numToArr(max(arrToNum(addamount) // 2, 1))

                if mechs[Task.PARTY] == -1:
                    ui.note(f"We found some money on the ground! Fit {arrToNum(addamount)} more into our bag.", 0)
                else:
                    ui.note(f"We made some money! Fit {arrToNum(addamount)} more into our bag.", 0)

                ui.close()
                coins, trades = cointrade.coinTrade(coins, addamount, True, mechlevel)
                ui = MainUI(image_dir="mainimages")

                mechs[Task.COIN] = upgradeCoins(trades)

            case "party":
                if mechs[Task.PARTY] == 100:
                    ui.note("This work is beneath you now. You know what that means...employee time!", 1)
                else:
                    max_kids = mechs[Task.PARTY]
                    num_kids = random.randint(2, max_kids)
                    ui.note(f"A party with {num_kids} just came in! A server will take their order, you'll make the pizzas!", 0)

                    ui.close()
                    enough, needed, cupcakes, rem = bdayparty.playParty(num_kids)
                    ui = MainUI(image_dir="mainimages")

                    mechs[Task.PARTY] = updateParty(enough, needed, cupcakes, rem, num_kids)

                    taskqueue.append("party")
                    taskqueue.append("cointradep")

            case "slice":
                double = False
                if mechs[Task.COUNTER][0] == 1:
                    double = True
                if not double:
                    ui.note(f"We've got customers!", 0)
                else:
                    ui.note(f"We've got customers! There's a two at once special today, so most people are coming in pairs!", 0)

                tot_rounds = mechs[Task.COUNTER][1]
                time_limit = mechs[Task.COUNTER][2]

                ui.close()
                cut, plate, time, actual_rounds = bySlice.serveCustomers(tot_rounds, time_limit, double)
                ui = MainUI(image_dir="mainimages")

                updateSlice(cut, plate, time, actual_rounds, double)

                taskqueue.append("slice")
                taskqueue.append("cointradep")


def updateGroceryStats(items_goal, time_goal, total_items, final_time, mistakes, taskqueue):
    new_total = items_goal
    new_time = time_goal

    good = mistakes[0] > -(-total_items // 2)

    ## if they didn't get to all the items, but they answered well without too many hints, increase time limit
    ## if they didn't answer well, decrease number of items
    if items_goal > total_items:
        if good:
            new_time += 20
        else:
            new_total = max(3, total_items)
    else:
        ## got all the answers. Increase amount if answered well. Decrease time if not answered well.
        if good:
            new_total = min(15, total_items + 3)
        else:
            new_time = max(30, final_time - 20)

        ## good enough to start party
        if total_items >= 6 and items_goal == total_items == mistakes[0] and mechs[Task.PARTY] == -1:
            ## party and slice become available  
            taskqueue.append("party")
            taskqueue.append("cointradep")
            mechs[Task.PARTY] = 2
            taskqueue.append("slice")
            taskqueue.append("cointradep")
            mechs[Task.COUNTER][0] = 0
        
        ## mastery achieved
        if total_items >= 15 and final_time <= 90:
            ## This is the only one where time is considered for mastery because the goal is immediate recognition, without counting.
            mechs[Task.GROCERY][0] = 1

    return new_total, new_time

def updateSnakeStats(lvl, time_goal, snake_goal, t_attempts, h_attempts, caught, final_time):
    new_level = lvl
    new_level_head = 0
    new_time = time_goal
    new_snake = snake_goal

    points = 0.0
    for snake in t_attempts:
        if snake[0] == 1: ## got it in one go
            points += 1
        elif snake[0] <= snake[1] / 10 + 1: # got it by counting 10s
            points += 0.8
        elif snake[0] <= snake[1] / 5 + 1: # got it by counting 5s
            points += 0.5

    tailgood = False
    if points/caught > 0.5:
        tailgood = True

    headgood = h_attempts[0] > -(-caught // 2)

    ## if they didn't get to all the snakes, but they answered well without too many hints, increase time limit
    ## if they didn't answer well, decrease number of snakes
    if snake_goal > caught:
        if headgood:
            new_time += 20
        else:
            new_snake = max(3, caught)
    else:
        ## got all the answers. Increase amount if answered well. Decrease time if not answered well.
        if headgood:
            new_snake = caught + 3
        else:
             new_time = max(30, final_time - 20)
        ## if no mistakes and all snakes caught, consider mastered
        if h_attempts[0] == caught and caught >= 9:
            new_level_head = 1

    ## promote to 1 no matter what so that now the player doesn't necessarily start at square 0
    if lvl == 0:
        new_level = 1

    if points/caught == 1:
        new_level = 2 ## intention is to skip the tail catching if new_level reaches 2

    return new_level, new_level_head, new_time, new_snake

def arrToNum(arr):
    num = arr[3] * 1000 + arr[2] * 100 + arr[1] * 10 + arr[0]
    return num

def numToArr(num):
    working = num
    index = 0
    toReturn = [0,0,0,0]

    while working != 0:
        toReturn[index] = working % 10
        working = working // 10
        index += 1

    return toReturn


def upgradeCoins(trades):
    match mechs[Task.COIN]:
        case 0:
            if trades <= 1: 
                return 1
        case 1:
            if trades <= 4 and coins[1] != 0:
                return 2
            else:
                return 1
        case 2:
            if trades <= 6 and coins[2] != 0:
                return 3
            else:
                return 2
        case 3:
            return 3

def updateParty(enough, needed, cupcakes, rem, num_kids):
    ## not all input used, but there in case of future update for more sensitive level management
    if enough == needed == cupcakes == rem == 1 and num_kids >= 8:
        return 100
    elif needed <= 3 and cupcakes <= 3:
        return min(12, max(num_kids + 2, mechs[Task.PARTY])) ## can increase the 10 to more later

def updateSlice(cut, plate, time, rounds, double):
    if sum(cut) == sum(plate) == rounds == mechs[Task.COUNTER][1] and rounds >= 4:
        if not double:
            mechs[Task.COUNTER][0] = 1
    
    ## round up
    good_cut = sum(cut) > -(-rounds // 2)
    good_plate = sum(plate) > -(-rounds//2)

    ## if doing good, and in time (as in, all rounds done), increase rounds
    if good_cut and good_plate and rounds == mechs[Task.COUNTER][1]:
        mechs[Task.COUNTER][1] += 2
    ## if doing good, but out of time, increase time
    elif good_cut and good_plate:
        mechs[Task.COUNTER][2] += 20
    ## if doing bad, decrease rounds AND time
    else:
        mechs[Task.COUNTER][1] = max(2, rounds - 2)
        mechs[Task.COUNTER][2] = max(60, time - 20)
        
runShop()



