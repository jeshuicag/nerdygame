import random
from party_ui import PartyUI

def playParty(num_kids):
    global ui
    ui = PartyUI(image_dir="partyimages", toppings_dir="shopimages")

    ## only the ones that i think make sense as toppings (ie, not salt, sugar, oil, etc)
    toppings = ["pineapple", "onion", "olive", "bellpepper", "mushroom", "pepperoni"]
    
    top_inventory = []
    top_per_kid =[]

    ## randomize order and inventory
    for topping in toppings:
        tpk = random.randint(1,10)
        top_per_kid.append(tpk)
        top_inventory.append(random.randint(0, num_kids*tpk*2))

    # check if enough
    mistakes, num_enough_mistakes = askIfEnough(num_kids, top_per_kid, top_inventory, toppings)

    # ask for how much more is needed
    num_inv_mistakes = howMuchMoreNeeded(num_kids, top_per_kid, top_inventory, mistakes, toppings)

    # randomize amount of cupcakes
    per_kid = random.randint(1,5)
    remainder = random.randint(0, num_kids - 1)
    cakes = num_kids * per_kid + remainder

    # ask about cupcakes
    num_cupcake_mistakes, num_rem_mistakes = splitCupcakes(num_kids, cakes, per_kid, remainder)

    ui.close()

    return num_enough_mistakes, num_inv_mistakes, num_cupcake_mistakes, num_rem_mistakes


##  phase 3, cupcake event
def splitCupcakes(num_kids, num_cakes, pkid, rem):
    allow_cupcake_visual = False
    answer1 = 0
    answer2 = 0
    fails = 0
    
    # hint leves
    text = f"Pizzas going out! But what's a party without cake? We have {num_cakes} cupcakes and {num_kids} kids. How many cupcakes can I give each kid? Everyone needs the same amount of cupcakes! We can eat leftovers."
    while answer1 != pkid:
        if fails == 1:
            if answer1 > pkid:
                text = f"I just tried to give everyone {answer1} and there's not enough cupcakes! Luckily no one eats until we sing happy birthday, so I can redistribute them...We have {num_cakes} cupcakes and {num_kids} kids. How many cupcakes should I give each kid?"
            else:
                text = f"I just gave everyone {answer1}, but there's still so many left! Surely we can give more! We have {num_cakes} cupcakes and {num_kids} kids. How many cupcakes should I give each kid?"
        if fails >= 2:
            text = f"Why don't you sort them onto these plates, and I'll just bring them out. We have {num_cakes} cupcakes and {num_kids} kids. How many cupcakes does each kid end up with?"
            allow_cupcake_visual = True

        ## input 2 and 3 are for toppings, not relevant here
        ui.display(text, None, None)
        answer1 = ui.quest(allow_cupcake_visual, num_kids, num_cakes)
        fails += 1

    text = f"{answer1} per kid...how many does that leave for us to eat?"
    rem_fails = 0

    while answer2 != rem:
        if rem_fails >= 1:
            text = f"Hm..check again. After we give each kid {pkid}, how many are left?"
        ui.display(text, None, None)
        answer2 = ui.quest(allow_cupcake_visual, num_kids, num_cakes)
        allow_cupcake_visual = True
        rem_fails += 1

    return fails, rem_fails

# phase 1, checklist event
def askIfEnough(num_kids, tpk, t_inv, toppings):

    ## 0 is has enough and said enough, 1 is has enough but didn't say that, 
    ## 2 is too little and answered too little, 3 is too little but didn't answer that
    mistakes = [-1 for i in range(len(tpk))]

    allow_pizza_visual = False

    # data for later calculation of mechlevel
    fails = 0

    ui.server(f"Order up! We have a party with {num_kids} kids. Everyone wants this amount of toppings:", tpk, toppings)

    while not all(mistake%2 == 0 for mistake in mistakes):

        # different hint levels, eventually switch between two just to indicate submission was acknowledged
        if fails == 1:
            allow_pizza_visual = True
            ui.server(f"Why don't you go ahead and starting making the order. Let me know what ingredients you need more of. Remember, there are {num_kids} kids, and each one wants the same things on their pizza:", tpk, toppings)
        elif fails != 0 and fails%2 == 0:
            ui.server(f"Try putting one piece per pizza until each pizza has enough. If you can't, we don't have enough! Remember, there are {num_kids} kids, and each one wants the same things on their pizza:", tpk, toppings)
        elif fails % 2 == 1:
            ui.server(f"That doesn't seem right... Remember, there are {num_kids} kids, and each one wants the same things on their pizza:", tpk, toppings)
        
        ## should return array of 0 and 1 that parallels toppings list that indicates if player said its enough (0) or not enough (1)
        enough = ui.askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual)

        ## check answer and update mistakes
        for i, inStorage in enumerate(t_inv):
            if inStorage >= tpk[i] * num_kids and enough[i] == 0:
                mistakes[i] = 0
            elif inStorage >= tpk[i] * num_kids:
                mistakes[i] = 1
            elif inStorage < tpk[i] * num_kids and enough[i] == 1:
                mistakes[i] = 2
            elif inStorage < tpk[i] * num_kids:
                mistakes[i] = 3
        
        fails += 1

    return mistakes, fails

# phase 2, shopping list event
def howMuchMoreNeeded(kids, tpk, t_inv, mistakes, toppings):

    # 0 for correct amount, 1 for too much added, 2 for too little
    warnings = [-1 for i in range(len(toppings))]

    # store answers the player gives
    added = [0 for i in range(len(toppings))]

    allow_pizza_visual = False
    fails = 0

    ui.server(f"Alright! How much more of those do you need, exactly? It's not in my job description, but I'll do a quick grocery run with my own money. Please don't buy more than we need. Remember, there are {kids} kids and each one wants the same order!", tpk, toppings)

    while sum(warnings) != 0:

        # hint levels
        if fails == 1:
            allow_pizza_visual = True
            ui.server(f"Start making the pizzas and let me know how much more of each ingredient you need! Remember, there are {kids} kids and each wants:", tpk, toppings)
        elif fails != 0 and fails%2 == 0:
            ui.server(f"Try putting one piece per pizza until each pizza has enough. Then count how many more you need per pizza and add them up! Remember, there are {kids} kids, and each one wants the same things on their pizza:", tpk, toppings)
        elif fails%2 == 1:
            ui.server(f"You can also make one pizza at a time until you run out of ingredients! Remember, there are {kids} kids, and each one wants the same things on their pizza:", tpk, toppings)

        # should return how much of each item the player is trying to add.
        ## prompt should take the indexes in mistakes with values 2 (parallel array to toppings) to ask the player how much more is needed.
        added = ui.prompt(kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual)

        # update mistakes accordingly
        for i, add in enumerate(added):
            if mistakes[i] == 2:
                if t_inv[i] + add == tpk[i] * kids:
                    warnings[i] = 0
                elif t_inv[i] + add > tpk[i] * kids:
                    warnings[i] = 1
                else:
                    warnings[i] = 2
            else:
                warnings[i] = 0
        
        fails+=1

    return fails

# for testing
# playParty(3)


    