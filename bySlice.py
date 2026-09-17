from slice_ui import SliceUI
import time
import random

ui = SliceUI(image_dir="sliceimages")

UNDERLINE = '\033[4m'

## double means two customers at once
def serveCustomers(tot_rounds, time_limit, double):
    start_time = time.time()
    rounds = 0

    while (rounds < tot_rounds and time.time() - start_time < time_limit):
        denom = random.randint(1, 5)
        numer = random.randint(1, denom * 2)
        denom2 = None
        numer2 = None

        if double:
            denom2 = random.randint(1, 5)
            numer2 = random.randint(1, denom2 * 2)

        ui.speak(f"I'd like {numer}/{denom} pizza")
        
        if denom2:
            ui.speak2(f"I'd like {numer2}/{denom2} pizza")

        cutPizza(numer, denom, numer2, denom2)

        handOver(numer, denom, numer2, denom2)

        rounds += 1
    
def cutPizza(numer, denom, numer2, denom2):
    slice1 = 0
    slice2 = 0

    hint_level = 0

    while (slice1 != denom or slice2 != denom2):

        ## should also have a "new pizza" button
        ## as long as denom2 is not None, makeCuts knows that two pizzas are available and that both need to be cut
        slice1, slice2 = ui.makeCuts(denom2)

        text = denom
        if hint_level >= 2:
            text = f"{UNDERLINE}{denom}{UNDERLINE}"
        text2 = denom2
        if hint_level >= 2 and denom2:
            text2 = f"{UNDERLINE}{denom2}{UNDERLINE}"

        if slice1 < denom:
            ui.speak(f"Hey! Those slices are too big! I want {numer}/{text} pizza!")
        elif slice1 > denom:
            ui.speak(f"Hey! Those slices are too small! I want {numer}/{text} pizza!")
        else:
            ui.speak("Perfect!")
        if denom2:
            if slice2 < denom2:
                ui.speak2(f"Hey! Those slices are too big! I want {numer2}/{text2} pizza!")
            elif slice2 > denom2:
                ui.speak2(f"Hey! Those slices are too small! I want {numer2}/{text2} pizza!")
            else:
                ui.speak2("Perfect!")

        hint_level += 1

def handOver(numer, denom, numer2, denom2):
    slices1 = 0
    slices2 = 0

    hint_level = 0

    while (slices1 != numer or slices2 != numer2):

        ## as long as denom2 is not None, onPlate knows that there are two pizzas cut with the specified amount of slices
        slices1, slices2 = ui.onPlate(denom, denom2)

        text = numer
        if hint_level >= 2:
            text = f"{UNDERLINE}{numer}{UNDERLINE}"
        text2 = numer2
        if hint_level >= 2 and numer2:
            text2 = f"{UNDERLINE}{numer2}{UNDERLINE}"

        if slices1 < numer:
            ui.speak(f"Hey! That's not enough slices! I want {text}/{denom} pizza!")
        elif slices1 > numer:
            ui.speak(f"Hey! That's too many slices! I want {text}/{denom} pizza!")
        else:
            ui.speak("Thanks!")
        if numer2:
            if slices2 < numer2:
                ui.speak2(f"Hey! That's not enough slices! I want {text2}/{denom2} pizza!")
            elif slices2 > numer2:
                ui.speak2(f"Hey! That's too many slices! I want {text2}/{denom2} pizza!")
            else:
                ui.speak2("Thanks!")

        hint_level += 1


    



