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
    answer1 = 0
    answer2 = 0
    fails = 0

    text = f"Pizzas going out! But what's a party without cake? We have {num_cakes} cupcakes. How many cupcakes can I give each kid?"
    while answer1 != pkid:
        if fails == 1:
            if answer1 > pkid:
                text = f"I just tried to give everyone {answer1} and there's not enough cupcakes! Luckily no one eats until we sign happy birthday, so i can redistribute them...We have {num_cakes} cupcakes and {num_kids} kids. How many cupcakes should I give each kid?"
            else:
                text = f"I just gave everyone {answer1}, but there's still so many left! Surely we can give more! We have {num_cakes} cupcakes and {num_kids} kids. How many cupcakes should I give each kid?"
        if fails >= 2:
            text = f"Why don't you sort them onto these plates, and I'll just bring them out. We have {num_cakes} cupcakes and {num_kids} kids."
            allow_cupcake_visual = True
        ## plated indicates whether to show pkid cupcakes on each plate or to let the player add the cupcakes themselves when allow_cupcake_visual is true
        ui.display(text, None, None)
        answer1 = ui.quest(allow_cupcake_visual, num_kids, num_cakes)
        fails += 1

    text = f"{answer1} per kid...how many does that leave for us to eat?"
    fails = 0

    while answer2 != rem:
        if fails >= 1:
            text = f"Hm..check again. After we give each kid {pkid}, how many are left?"
        ui.display(text, None, None)
        answer2 = ui.quest(allow_cupcake_visual, num_kids, num_cakes)
        allow_cupcake_visual = True
        fails += 1

def askIfEnough(num_kids, tpk, t_inv, toppings):
    ## 0 is has enough and said enough, 1 is has enough but didn't say that, 
    ## 2 is too little and answered too little, 3 is too little but didn't answer that
    mistakes = [-1 for i in range(len(tpk))]
    allow_pizza_visual = False

    ui.server(f"Order up! We have a party with {num_kids} kids. Everyone wants the same amount of pizza toppings. Do we have enough to complete this order?", tpk, toppings)

    while not all(mistake%2 == 0 for mistake in mistakes):
        if allow_pizza_visual:
            ui.server(f"Why don't you go ahead and starting making the order. Let me know what ingredients you need more of. Remember, there are {num_kids} kids, and this is each one wants the same things on their pizza:", tpk, toppings)
        ## should return array of 0 and 1 that parallels toppings list that indicates if player said its enough (0) or not enough (1)
        enough = ui.askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual)

        for i, inStorage in enumerate(t_inv):
            if inStorage >= tpk[i] * num_kids and enough[i] == 0:
                mistakes[i] = 0
            elif inStorage >= tpk[i] * num_kids:
                mistakes[i] = 1
                allow_pizza_visual = True
            elif inStorage < tpk[i] * num_kids and enough[i] == 1:
                mistakes[i] = 2
            elif inStorage < tpk[i] * num_kids:
                mistakes[i] = 3
                allow_pizza_visual = True

    return mistakes

def howMuchMoreNeeded(kids, tpk, t_inv, mistakes, toppings):
    # 0 for correct amount, 1 for too much added, 2 for too little
    warnings = [-1 for i in range(len(toppings))]
    added = [0 for i in range(len(toppings))]
    allow_pizza_visual = False

    ui.server(f"Alright! How much more of those do you need, exactly? Make me a list, I'll do a quick grocery run. I only have a little bit of money, though, so we can't buy more than we need. Remember, there are {kids} kids and each one wants the same order!", tpk, toppings)

    while sum(warnings) != 0:
        # should return how much of each item the player is trying to add.
        ## prompt should take the indexes in mistakes with values 2 (parallel array to toppings) to ask the player how much more is needed.
        if allow_pizza_visual:
            ui.server(f"Start making the pizzas and let me know how much more of each ingredient you need! Remember, there are {kids} kids and each wants:", tpk, toppings)

        added = ui.prompt(kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual)

        for i, add in enumerate(added):
                if t_inv[i] + add == tpk[i] * kids:
                    warnings[i] = 0
                elif t_inv[i] + add > tpk[i] * kids:
                    warnings[i] = 1
                    allow_pizza_visual = True
                else:
                    warnings[i] = 2
                    allow_pizza_visual = True

playParty(2)


    