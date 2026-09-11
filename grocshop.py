import random

from grocery_ui import GroceryShopUI

mistake_level = 0
indicate_direction = False
indicate_number = False


def go_shopping(num_items):

    items = ["pineapple", "onion", "olive", "bellpepper", "mushroom", "butter", "cheese", "flour", "garlic", "herbs", "ketchup", "salt", "sugar", "yeast", "oil"]
    
    random.shuffle(items)

    ui = GroceryShopUI(image_dir="shopimages")
    try:
        for i, item in enumerate(items):
            prompt = random.randint(1, 20)

            while True and i < num_items:
                # receive answer from the card the player locks in
                answer = ui.ask(
                    prompt,
                    item,
                    indicate_direction=indicate_direction,
                    indicate_number=indicate_number,
                )

                if answer is None:          # player closed the window
                    return

                if answer == prompt:
                    change_mistake_level(max(0, mistake_level - 1))
                    break
                else:
                    change_mistake_level(min(3, mistake_level + 1))
    finally:
        ui.close()


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


go_shopping(10)
