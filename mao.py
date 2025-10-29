import core.cardgamecore as cardGameCore
import time

#work in progress
ruleDict = {
    'A': "reverse",
    '8': "skip",
    '7': "have a nice day"
}

def printWelcomeScreen(topCard):
    print("This is the game of MAO\n")
    time.sleep(2)
    print("There are 5 base rules and 0 additional rules\n")
    time.sleep(2)
    print("The game will continue to the right of Player 1 and will start with a %s of %s\n" % (str(topCard.value), topCard.suit))
    time.sleep(2)
    print("Begin\n\n")

if __name__ == "__main__":
    #Welcome Message
    print("Welcome to MAO\n")

    #Initialize Piles
    print("Intializing Deck")
    drawPile = cardGameCore.Deck()
    placePile = cardGameCore.Deck()
    #Add cards to draw pile
    for suit in ["Clubs", "Spades", "Diamonds", "Hearts"]:
        for value in range(1,14):
            if value == 1:
                cardVal = 'A'
            elif value == 11:
                cardVal = 'J'
            elif value == 12:
                cardVal = 'Q'
            elif value == 13:
                cardVal = 'K'
            else:
                cardVal = str(value)
            drawPile.placeCardOnBottom(cardGameCore.Card(suit, cardVal))
    print("Deck Initialized")
    #shuffle pile
    drawPile.shuffleDeck()
    print("Deck Shuffled")

    #Initialize game logic
    numPlayers = int(input("\nHow many players?(3-6) \n  "))
    players = []
    for i in range(numPlayers):
        name = input("Player %d what is your name? \n  " % (i+1))
        players.append(cardGameCore.Player(name))   

    #Deal out cards
    for player in players:
        for i in range(7):
            player.giveCard(drawPile.getTopCard())
    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")      

    #Game text
    topCard = drawPile.getTopCard()
    placePile.placeCardOnTop(topCard)
    printWelcomeScreen(topCard)

    #Initialize game variables
    done = False
    skip = False
    revSkip = False
    reverse = False

    #Game loop
    while not done:
        #For each player
        for i in range(len(players)):
            #check draw pile
            if drawPile.empty():
                print("Draw Pile Empty ... \nRedistributing")
                top = placePile.getTopCard()
                while not placePile.empty():
                    drawPile.placeCardOnTop(placePile.getTopCard())
                drawPile.shuffleDeck()
                
            #Check order of play
            if reverse:
                player = players[len(players)-i-3]
            else:
                player = players[i]
            
            #if players turn
            if not skip and not revSkip:
                #Player confirmation
                input("%s press enter play" % (player.name))

                #Game exit condition
                if len(player.hand) == 0:
                    done = True
                    break
                
                #loop until valid move is made
                validMove = False
                while not validMove:
                    #Show info
                    print("Top Card:")
                    topCard.printCard()
                    player.printHand()

                    #Get player move
                    move = input("Draw or Place a Card? (d or p)\n").strip().lower()
                    
                    # Handle empty input
                    if not move:
                        print("Please enter 'd' to draw or 'p' to place a card")
                        continue

                    # Handle invalid input
                    if move not in ['d', 'p', 'q']:
                        print("Invalid move. Please enter 'd' to draw, 'p' to place a card, or 'q' to quit.")
                        continue

                    #execute move
                    if move == 'd': #Draw
                        validMove = True
                        player.giveCard(drawPile.getTopCard())
                    elif move == 'p': #Place
                        # Check if hand is empty
                        if len(player.hand) == 0:
                            print("You have no cards to place! Drawing a card instead.")
                            validMove = True
                            player.giveCard(drawPile.getTopCard())
                        else:
                            #get chosen card
                            choice = input("Which card would you like to place?\n").strip()
                            
                            # Handle empty input
                            if not choice:
                                print("Please enter a card number")
                                validMove = False
                                continue
                            
                            # Try to convert to integer
                            try:
                                choice_num = int(choice)
                            except ValueError:
                                print("Please enter a valid number")
                                validMove = False
                                continue
                            
                            # Validate card number range
                            if choice_num < 1:
                                print("Card number must be at least 1")
                                validMove = False
                                continue
                            elif choice_num > len(player.hand):
                                print("Card selection not valid. You only have %d card(s) in your hand." % len(player.hand))
                                validMove = False
                                continue
                            else:
                                validMove = True
                                cardChosen = player.playCard(choice_num)
                            
                            #check chosen card is a valid placement
                            if cardChosen.suit == topCard.suit or cardChosen.value == topCard.value:
                                #check if there is a rule involved
                                    #Will replace in future with ruleDict
                                if cardChosen.value == str('8'):
                                    skip = True
                                elif cardChosen.value == str('A'):
                                    reverse ^= True
                                    skip = True
                                elif cardChosen.value == str('7'):
                                    before = time.time()
                                    response = input()
                                    after = time.time()
                                    if ((after - before) > 7) or (response.lower() != "have a nice day"):
                                        print("Failure to follow a rule, you get a card")
                                        player.giveCard(drawPile.getTopCard())
                                    else:
                                        print("Congrats you took %.2f seconds" % ((after - before)))

                                #Confirm players chosen card
                                print("Player chose %s of %s" % (str(cardChosen.value), cardChosen.suit))
                                placePile.placeCardOnTop(cardChosen)

                                #update top card
                                topCard = cardChosen
                            else:
                                #House rule on misplacing a card
                                print("Stupidity\n\tYou get a card")
                                stupidityCard = placePile.getTopCard()
                                player.giveCard(stupidityCard)
                                player.giveCard(drawPile.getTopCard())

                    elif move == 'q': #Rule added to quit
                        validMove = True
                        done = True
                        break

                #End of player turn
                input("Press enter and pass to next player")
                print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
            else : #Player was skipped or skipped over for reverse
                skip = False
            if done:
                break
            if len(player.hand) == 0:
                done = True
                print("\n\n Player %s Won!!!" % (player.name))