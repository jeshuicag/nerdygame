import random
import time

from grocery_ui import GroceryShopUI

mistake_level = 0
indicate_direction = False
indicate_number = False


def go_shopping(num_items, time_limit):
    start_time = time.time()
    curr_tot = 0
    mistakes = [0, 0, 0, 0]

    items = ["pineapple", "onion", "olive", "bellpepper", "mushroom", "butter", "cheese", "flour", "garlic", "herbs", "ketchup", "salt", "sugar", "yeast", "oil"]
    
    random.shuffle(items)

    ui = GroceryShopUI(image_dir="shopimages")
    
    while (time.time() - start_time < time_limit and curr_tot < num_items):
        item = items[curr_tot]
        prompt = random.randint(1, 20)
        answer = 0

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
                change_mistake_level(min(3, mistake_level + 1))

        mistakes[mistake_level] += 1
        change_mistake_level(max(0, mistake_level - 1))
            
        curr_tot += 1

    ui.close()
    return curr_tot, time.time() - start_time, mistakes


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


## go_shopping(10, 120)
