import random
import time
from grocery_ui import GroceryShopUI

mistake_level = 0
indicate_direction = False
indicate_number = False

## function to call in main
def go_shopping(num_items, time_limit):
    global ui
    ui = GroceryShopUI(image_dir="shopimages")

    ## counters
    start_time = time.time()
    curr_tot = 0
    mistakes = [0, 0, 0, 0]

    ## match name of png
    items = ["pineapple", "onion", "olive", "bellpepper", "mushroom", "butter", "cheese", "flour", "garlic", "herbs", "ketchup", "salt", "sugar", "yeast", "oil"]
    
    ## shuffle for randomness
    random.shuffle(items)
    
    ## keep session short if the goal amount is too difficult since kids will feel discouraged
    while (time.time() - start_time < time_limit and curr_tot < num_items):
        item = items[curr_tot]
        prompt = random.randint(1, 20)
        answer = 0

        ## get back the card they picked
        while answer != prompt:
            answer = ui.ask(
                prompt,
                item,
                indicate_direction=indicate_direction,
                indicate_number=indicate_number,
            )

            if answer == None:
                ui.close()
                return curr_tot, time.time() - start_time, mistakes

            if answer != prompt:
                ## two levels to hints-- first nothing, then show direction to go in, then show number on card.
                change_mistake_level(min(3, mistake_level + 1))

        # track what level of hint was needed to get the right answer, to calculate minigame mastery
        mistakes[mistake_level] += 1
        # once answer is gotten, go down a level for next round. max hint level is 3, so that 2 and 3 both show the most extreme hint
        change_mistake_level(max(0, mistake_level - 1))
            
        curr_tot += 1

    ui.close()
    return curr_tot, time.time() - start_time, mistakes

## set if we indicate direction or number next time those are fed to the ui call
def change_mistake_level(new_level):
    global mistake_level, indicate_direction, indicate_number
    if mistake_level != new_level:
        mistake_level = new_level
        match new_level:
            case 0:
                indicate_direction = False
                indicate_number = False
            case 1:
                indicate_direction = True
                indicate_number = False
            case 2 | 3:
                indicate_direction = True
                indicate_number = True


## for testing
# go_shopping(10, 120)
