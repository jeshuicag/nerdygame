import random
from snake_ui import SnakeHuntUI
import time

def catchSnake(player_place, time_limit, snake_limit):
    global ui
    ui = SnakeHuntUI(image_dir="snakeimages")

    mistake_level = 0
    start_time = time.time()
    num_snakes = 0
    snake_tail = 0
    snake_head = 0
    snake_len = 0

    catch_tail_tries = []
    shout_head_count = [0, 0, 0, 0]

    ## keep session short for attention span
    while time.time() - start_time < time_limit and num_snakes < snake_limit:

        # generate random snake within 20 places of player
        direction = random.choice((-1,1))

        # take care of edge case where player is on edge of board; snake must be at least 3
        if player_place > 117:
            direction = -1
        if player_place < 4:
            direction = 1

        # Make sure dist allows for at least 3 spaces
        if direction == 1:
            dist = min(random.randint(1, 20), 118 - player_place)
        else:
            dist = min(random.randint(1, 20), player_place - 3)

        snake_tail = player_place + direction * dist

        # make sure len fits on board
        if direction == 1:
            snake_len = min(random.randint(1,10), 120 - snake_tail)
        else:
            snake_len = min(random.randint(1,10), snake_tail - 1)

        snake_head = snake_tail + snake_len * direction

        # catch the tail
        num_tries_tail = 0
        
        distance = player_place - snake_tail

        while player_place != snake_tail:
            ## print(f"Player: {player_place}, Dir: {direction}, Dist: {dist}, Tail: {snake_tail}, Len: {snake_len}, Head: {snake_head}")
            old_place = player_place
            player_place = catch_tail(player_place, snake_tail, snake_head, direction, snake_len)

            if player_place <= 120 and player_place >= 1:
                ui.moveplayer(player_place)

            temp = checkplace(player_place, snake_head, snake_tail)

            if temp == 0:
                player_place = old_place
                ui.moveplayer(player_place)
            else:
                direction = temp

            num_tries_tail += 1

        catch_tail_tries.append([num_tries_tail, distance])
        
        ## print(f"Player: {player_place}, Dir: {direction}, Dist: {dist}, Tail: {snake_tail}, Len: {snake_len}, Head: {snake_head}")
        # signal the head
        while shout_head(snake_tail, snake_head, mistake_level, snake_len) != snake_head:
            mistake_level = min(mistake_level + 1, 3)

        shout_head_count[mistake_level] += 1

        mistake_level = max(0, mistake_level - 1)
        num_snakes += 1

    ui.close()

    return catch_tail_tries, shout_head_count, num_snakes, time.time() - start_time

        
def catch_tail(place, tail, head, direc, len):
    answer = ui.asktail(place, tail, head)
    return max(1, min(120, place + answer))

def shout_head(tail, head, mis_level, len):
    answer = ui.askhead(tail, head, mis_level, len)
    return answer

# in case player jumps on or over snake, go back to original place or change dir
def checkplace(place, head, tail):
    if (place <= head and place > tail) or (place >= head and place < tail):
        return 0
    if place < head:
        return 1
    if place > head:
        return -1

# try:
#     catchSnake(1, 120, 5)
# finally:
#     ui.close()





