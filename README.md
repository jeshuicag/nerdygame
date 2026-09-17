For Nerdy 2026 Hackathon

K-5 math game for teaching and maintaining foundations in the context of running a pizza shop. Maybe call it Pepperoni Snakes.

Grocery store: Buy items in a list. Player is presented with cards that have visual representation of numbers in order. Prompted to scroll to the correct amount using the +/- buttons. (Ex: 5 bags of flour, scroll to 5. Then 3 tomatoes, scroll from 5 to 3). Targeted at K, for recognizing numbers while giving a sense of comparison.

run grocery store: /opt/anaconda3/bin/python3.12 grocshop.py


Partnered Snake Hunt: 12 x 10 board that functions as a 1D board (can't move vertically). Player is given the number of the square they are standing on. Snake is somewhere nearby. Enter amount to move in order to 'catch the snake's tail'. Once caught, shout out what square the head is at for partner to finish capture. Catching the snake tail only requires seeing amount that needs to be moved + direction of movement and putting a number to it. Telling partner where the head is using only current space number and length of snake introduces simple addition/ subtraction. Targeted for 1st grade.

run snake hunt: /opt/anaconda3/bin/python3.12 snakehunt.py

Cashier: Copper coin worth 1. Iron worth 10. Gold worth 100. Diamond worth 1000. Use to teach place values. Coin limit is 9, whenever it's hit, make the player do manual conversion from one type of coin to the next to enforce base 10. Occasionally pick up money and have player figure out how to add it to their existing money. Targeted for 1st and 2nd grade, become more complex to include multi-digit numbers as mastery improves.

run snake hunt: /opt/anaconda3/bin/python3.12 cointrade.py

Party: number of kids that all need the same amount of food. Use to teach multiplication/ division. Server tells player how many kids there are and how much food each one needs, and player figures out total amount of food. Player has certain amount of cupcakes and needs to figure out how many each kid will have, and also take away remainders. Start with parties of two to teach odd/even, then increase. Targeted to 2/3 grade, become more complex as mastery increases.

run party: /opt/anaconda3/bin/python3.12 bdayparty.py

Counter: Teach fractions by having customers ask for fractional amount of pizza. Player must cut pizza into denominator and serve correct amount. Targeted to 3/4 grade, fractions become more complex as mastery increases. Serve two customers at once to showcase value of different fractions, when fractions with different denominators are the same, etc etc.

Once mastery is reached, player can hire 'employees' to automate certain skills like grocery runs or cashier. Employees can occasionally ask higher level questions and also skill check questions, and will quit if player fails skill check.

Want to do:
- make cleaner backend/ frontend distinction. Front end should be simpler, backend should handle all logic. Some visual implementations that don't exist without a front end need extra logic and are currently implemented in the front end completely. Move it over to the backend. cointrade.py is the best example of a clean front end/ back end split.

- overall make the visuals more appealing/ thematic
    - make the party seem more like a party in the background, present it visually as less like a word problem, make items look more like what they should be
    - big motivation there is supposed to be fairness (kids naturally want things to be equal when everyone is sharing), so present it more in a 'if you get this wrong someone won't have an equal share' way

- add tutorials for first time playing each minigame

- tune level calculation and finance system

- employee system

- more advanced levels (multi-digit multiplication, bigger fractions)

- reinforce connection between things (smaller orders lead to less to add in next coin trade activity, using up ingredients means buying more in the next grocer run, etc)

