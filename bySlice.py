from slice_ui import SliceUI
import time
import random

UNDERLINE = '\033[4m'

## double means two customers at once
def serveCustomers(tot_rounds, time_limit, double):
    global ui
    ui = SliceUI(image_dir="sliceimages")

    start_time = time.time()
    rounds = 0

    # data for later level calculations
    cut_hints = []
    plate_hints = []

    while (rounds < tot_rounds and time.time() - start_time < time_limit):

        # generate fractions
        denom = random.randint(1, 5)
        numer = random.randint(1, denom * 2)
        denom2 = None
        numer2 = None

        # account for 2 customers at once (let the player get a sense for comparison between fractions)
        if double:
            denom2 = random.randint(1, 5)
            numer2 = random.randint(1, denom2 * 2)

        ui.speak(f"I'd like {numer}/{denom} pizza")
        
        if denom2:
            ui.speak2(f"I'd like {numer2}/{denom2} pizza")

        cut_hint = cutPizza(numer, denom, numer2, denom2)
        cut_hints.append(cut_hint)

        ui.speak(f"Please hand me {numer}/{denom} pizza")
        
        if denom2:
            ui.speak2(f"Please hand me {numer2}/{denom2} pizza")

        plate_hint = handOver(numer, denom, numer2, denom2)
        plate_hints.append(plate_hint)

        rounds += 1

    ui.close()

    return cut_hints, plate_hints, time.time() - start_time, rounds

# phase 1-- cut pizza to denominator size   
def cutPizza(numer, denom, numer2, denom2):
    ui.instruct("Cut the pizza to the right size!")

    slice1 = 0
    slice2 = 0

    # hint goes nothing, to indicating if slice is too big or small, to emphasizing the denominator
    hint_level = 0

    ## in case player gets one customer correct but not the other
    track1 = denom
    track2 = denom2

    while (slice1 != denom or slice2 != denom2):

        ## should also have a "new pizza" button
        ## as long as denom2 is not None, makeCuts knows that two pizzas are available and that both need to be cut
        slice1, slice2 = ui.makeCuts(denom2)

        text = denom

        if hint_level >= 1:
            text = f"{UNDERLINE}{denom}{UNDERLINE}"
        text2 = denom2
        if hint_level >= 1 and denom2:
            text2 = f"{UNDERLINE}{denom2}{UNDERLINE}"

        if track1:
            if slice1 < denom:
                ui.speak(f"Hey! Those slices are too big! I want {numer}/{text} pizza!")
            elif slice1 > denom:
                ui.speak(f"Hey! Those slices are too small! I want {numer}/{text} pizza!")
            else:
                ui.speak("Perfect!")
                track1 = None
        else:
            slice1 = denom

        if track2:
            if slice2 < denom2:
                ui.speak2(f"Hey! Those slices are too big! I want {numer2}/{text2} pizza!")
            elif slice2 > denom2:
                ui.speak2(f"Hey! Those slices are too small! I want {numer2}/{text2} pizza!")
            else:
                ui.speak2("Perfect!")
                track2 = None
        else:
            slice2 = denom

        hint_level += 1

    return hint_level

# phase two-- put numerator on plate
def handOver(numer, denom, numer2, denom2):
    ui.instruct("Put the right amount of pizza on the plate!")

    slices1 = 0
    slices2 = 0

    # hint goes nothing, to indicating if too many or few slices, to emphasizing the numerator
    hint_level = 0

    ## in case player gets one customer correct but not the other
    track1 = numer
    track2 = numer2

    while (slices1 != numer or slices2 != numer2):

        ## as long as denom2 is not None, onPlate knows that there are two pizzas cut with the specified amount of slices
        slices1, slices2 = ui.onPlate(denom, denom2)

        text = numer
        if hint_level >= 1:
            text = f"{UNDERLINE}{numer}{UNDERLINE}"
        text2 = numer2
        if hint_level >= 1 and numer2:
            text2 = f"{UNDERLINE}{numer2}{UNDERLINE}"

        if track1:
            if slices1 < numer:
                ui.speak(f"Hey! That's not enough slices! I want {text}/{denom} pizza!")
            elif slices1 > numer:
                ui.speak(f"Hey! That's too many slices! I want {text}/{denom} pizza!")
            else:
                ui.speak("Thanks!")
                track1 = None
                ui.customerServed()
        else:
            slices1 = numer
        if track2:
            if slices2 < numer2:
                ui.speak2(f"Hey! That's not enough slices! I want {text2}/{denom2} pizza!")
            elif slices2 > numer2:
                ui.speak2(f"Hey! That's too many slices! I want {text2}/{denom2} pizza!")
            else:
                ui.speak2("Thanks!")
                track2 = None
                ui.customerServed()
        else:
            slices2 = numer

        hint_level += 1
    
    return hint_level

## testing
serveCustomers(3, 180, True)

    



