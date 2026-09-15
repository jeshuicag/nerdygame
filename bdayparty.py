import random
from party_ui import PartyUI

ui = PartyUI(image_dir="partyimages", toppings_dir="shopimages")

def playParty(num_kids):
    toppings = ["pineapple", "onion", "olive", "bellpepper", "mushroom", "pepperoni"]
    top_inventory = []
    top_per_kid =[]

    ## randomize order and inventory
    for topping in toppings:
        tpk = random.randint(1,10)
        top_per_kid.append(tpk)
        top_inventory.append(random.randint(0, num_kids*tpk*2))

    mistakes = askIfEnough(num_kids, top_per_kid, top_inventory, toppings)

    howMuchMoreNeeded(num_kids, top_per_kid, top_inventory, mistakes, toppings)

    per_kid = random.randint(1,5)
    remainder = random.randint(0, num_kids - 1)
    cakes = num_kids * per_kid + remainder

    splitCupcakes(num_kids, cakes, per_kid, remainder)

def splitCupcakes(num_kids, num_cakes, pkid, rem):
    allow_cupcake_visual = False
    plated = False
    answer1 = 0
    answer2 = 0
    fails = 0

    text = f"We have {num_cakes} cupcakes. How many cupcakes can I give each kid?"
    while answer1 != pkid:
        if fails == 1:
            if answer1 > pkid:
                text = f"I just tried to give everyone {answer1} and there's not enough cupcakes! Luckily no one eats until we sign happy birthday, so i can redistribute them...How many cupcakes should I give each kid?"
            else:
                text = f"I just gave everyone {answer1}, but there's still so many left! Surely we can give more! How many cupcakes should I give each kid?"
        if fails >= 2:
            text = "Why don't you sort them onto these plates, and I'll just bring them out."
            allow_cupcake_visual = True
        ## plated indicates whether to show pkid cupcakes on each plate or to let the player add the cupcakes themselves when allow_cupcake_visual is true
        answer1 = ui.quest(text, num_kids, num_cakes, allow_cupcake_visual, plated, pkid, rem)
        fails += 1

    plated = True
    allow_cupcake_visual = False
    text = f"{answer1} per kid...how many does that leave for us to eat?"
    fails = 0

    while answer2 != rem:
        if fails >= 1:
            text = f"Hm..check again. After we give each kid {pkid}, how many are left?"
        answer2 = ui.quest(text, num_kids, num_cakes, allow_cupcake_visual, plated, pkid, rem)
        allow_cupcake_visual = True
        fails += 1

def askIfEnough(num_kids, tpk, t_inv, toppings):
    ## 0 is has too much and said too much, 1 is has too much but didn't say that, 
    ## 2 is too little and answered too little, 3 is too little but didn't answer that, 
    ## 4 is right amount and untouched, 5 is right amount but touched
    mistakes = [-1 for i in range(len(tpk))]

    allow_pizza_visual = False

    while not all(mistake%2 == 0 for mistake in mistakes):
        ## should return array of 0, 1, 2 that parallels toppings list that indicates if player said its too much (0), too little (1), or the right amount (2)
        enough = ui.askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual)

        for i, inStorage in enumerate(t_inv):
            if inStorage > tpk[i] * num_kids and enough[i] == 0:
                mistakes[i] = 0
            elif inStorage > tpk[i] * num_kids:
                mistakes[i] = 1
            elif inStorage < tpk[i] * num_kids and enough[i] == 1:
                mistakes[i] = 2
            elif inStorage < tpk[i] * num_kids:
                mistakes[i] = 3
            elif inStorage == tpk[i] * num_kids and enough[i] == 2:
                mistakes[i] = 4
            else:
                mistakes[i] = 5

        allow_pizza_visual = True

    ui.display("Alright! Let's see what else we need")

    return mistakes

def howMuchMoreNeeded(kids, tpk, t_inv, mistakes, toppings):
    # 0 for correct amount, 1 for too much added, 2 for too little
    warnings = [-1 for i in range(len(toppings))]
    added = [0 for i in range(len(toppings))]
    allow_pizza_visual = True

    while sum(warnings) != 0:
        # should return how much of each item the player is trying to add. 0 for the toppings that are 0 in notEnough.
        ## prompt should take the indexes in mistakes with values 0 or 2 and (parallel array to toppings) to ask the player how much more is needed from toppings they need more of and how much to put back in the fridge for toppings they have too much of.
        ## context: lets make a run to the fridge, how much should I put away and how much should i bring back?
        added = ui.prompt(kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual, added)

        for i, add in enumerate(added):
            if t_inv[i] + add == tpk[i] * kids:
                warnings[i] = 0
                #mistakes[i] = 4
            elif t_inv[i] + add > tpk[i] * kids:
                warnings[i] = 1
                #mistakes[i] = 0
            else:
                warnings[i] = 2
                #mistakes[i] = 2
        
        allow_pizza_visual = True

    ui.display("Pizzas going out! But what's a party without cake?")

playParty(2)


    