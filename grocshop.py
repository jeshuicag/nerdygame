import random

possible_items = ["pineapple", "onion", "olive", "bellpepper", "mushroom", "butter", "cheese", "flour", "garlic", "herbs", "ketchup", "salt", "sugar", "yeast", "oil"]

mistake_level = 0
indicate_direction = False
indicate_number = False


def go_shopping(items):

    random.shuffle(items)

    for item in items:
        png_path = "images/" + item + ".png"
        prompt = random.randint(1,20)

        while True:
            # receive answer
            answer = input(f"Get {prompt} {item}s: ")
            if int(answer) == prompt:
                change_mistake_level(max(0, mistake_level - 1))
                break

            else:
                change_mistake_level(min(3, mistake_level + 1))

def change_mistake_level(new_level):
    if mistake_level != new_level:
        match new_level:
            case 0:
                indicate_direction = False
                indicate_number = False
            case 1:
                indicate_direction = True
                indicate_number = False
            case 2 or 3:
                indicate_direction = True
                indicate_number = True

go_shopping(possible_items)
