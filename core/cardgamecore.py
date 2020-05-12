from random import shuffle
from collections import deque

suit = {
    'Hearts':'♥',
    'Diamonds':'♦',
    'Clubs':'♣',
    'Spades':'♠'
}

class Player:
    # Initializer / Instance Attributes
    def __init__(self, name):
        self.name = name
        self.hand = []
    
    def giveCard(self, card):
        self.hand.append(card)

    def playCard(self, handIndex):
        card = self.hand[handIndex-1]
        self.hand.remove(card)
        return card

    def printHand(self):
        print("Your hand:")
        for j in range(7):
            for i in range(9*len(self.hand)):
                if j == 0:
                    if i % 9 == 0 or i % 9 == 8:
                        print(" ", end="")
                    else:
                        print("_", end="")
                elif j == 6:
                    if i % 9 == 0 or i % 9 == 8:
                        print(" ", end="")
                    else:
                        print("-", end="")
                elif j == 1:
                    if i % 9 == 0 or i % 9 == 8:
                        print("|", end="")
                    elif i % 9 == 1:
                        print("%s" % (self.hand[int(i/9)].value)  , end="")
                    elif len(self.hand[int(i/9)].value) > 1 and i % 9 == 2:
                        pass
                    else:
                        print(' ', end='')
                elif j == 3:
                    if i % 9 == 0 or i % 9 == 8:
                        print("|", end="")
                    elif i % 9 == 4:
                        print("%s" % (suit[self.hand[int(i/9)].suit])  , end="")
                    else:
                        print(' ', end='')
                elif j == 5:
                    if i % 9 == 0 or i % 9 == 8:
                        print("|", end="")
                    elif i % 9 == 7 and len(self.hand[int(i/9)].value) > 1:
                        pass
                    elif i % 9 == 7 and len(self.hand[int(i/9)].value) == 1:
                        print("%s" % (self.hand[int(i/9)].value)  , end="")
                    elif len(self.hand[int(i/9)].value) > 1 and i % 9 == 6:
                        print("%s" % (self.hand[int(i/9)].value)  , end="")
                    else:
                        print(' ', end='')
                else:
                    if i % 9 == 0 or i % 9 == 8:
                        print('|', end='')
                    else:
                        print(' ', end='')
            print()

class Card:
    # Initializer / Instance Attributes
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def printCard(self):
        for j in range(7):
            for i in range(9):
                if j == 0:
                    if i % 9 == 0 or i % 9 == 8:
                        print(" ", end="")
                    else:
                        print("_", end="")
                elif j == 6:
                    if i % 9 == 0 or i % 9 == 8:
                        print(" ", end="")
                    else:
                        print("-", end="")
                elif j == 1:
                    if i % 9 == 0 or i % 9 == 8:
                        print("|", end="")
                    elif i % 9 == 1:
                        print("%s" % (self.value)  , end="")
                    elif len(self.value) > 1 and i % 9 == 2:
                        pass
                    else:
                        print(' ', end='')
                elif j == 3:
                    if i % 9 == 0 or i % 9 == 8:
                        print("|", end="")
                    elif i % 9 == 4:
                        print("%s" % (suit[self.suit])  , end="")
                    else:
                        print(' ', end='')
                elif j == 5:
                    if i % 9 == 0 or i % 9 == 8:
                        print("|", end="")
                    elif i % 9 == 7 and len(self.value) > 1:
                        pass
                    elif i % 9 == 7 and len(self.value) == 1:
                        print("%s" % (self.value)  , end="")
                    elif len(self.value) > 1 and i % 9 == 6:
                        print("%s" % (self.value)  , end="")
                    else:
                        print(' ', end='')
                else:
                    if i % 9 == 0 or i % 9 == 8:
                        print('|', end='')
                    else:
                        print(' ', end='')
            print()


class Deck:
    # Initializer / Instance Attributes
    def __init__(self):
        self.cards = deque()
    
    def shuffleDeck(self):
        shuffle(self.cards)
    
    def seeTopCard(self):
        top = self.cards.pop()
        self.cards.append(top)
        return top
    
    def getTopCard(self):
        return self.cards.pop()

    def placeCardOnTop(self, card):
        self.cards.append(card)
    
    def placeCardOnBottom(self, card):
        self.cards.appendleft(card)

    def empty(self):
        return not bool(self.cards)
