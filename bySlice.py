from slice_ui import SliceUI
import time
import random

ui = SliceUI(image_dir="sliceimages")

def serveCustomers(num_custs, time_limit):
    start_time = time.time()
    custs = 0

    while (custs < num_custs and time.time() - start_time < time_limit):
        denom = random.randomint(1, 5)
        numer = random.randomint(1, denom * 2)

        cut, given = ui.customer(denom, numer)

        cutPizza(denom)

        handOver(denom, numer)



    
def cutPizza(denom):
    slices = ui.makeCuts()
    while (slices != denom):
        if slices < denom:
            ui.speak("Hey! That slice is too big! Get a new pizza!")
        elif slices > denom:
            ui.speak("Hey! That slice is too small! Get a new pizza!")

    ui.speak("Perfect!")

    



