from random import shuffle
from collections import deque

suitSymbols = {
    'Hearts':'♥',
    'Diamonds':'♦',
    'Clubs':'♣',
    'Spades':'♠'
}

suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']


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

    #Pretty print for a hand of cards
    def printHand(self):
        print("Your hand:")
        if len(self.hand) == 0:
            print("(No cards in hand)")
            return
        
        # Display cards in rows of 7
        cards_per_row = 7
        for row_start in range(0, len(self.hand), cards_per_row):
            row_cards = self.hand[row_start:row_start + cards_per_row]
            
            # Print card numbers above the cards
            for card_idx in range(len(row_cards)):
                card_num = row_start + card_idx + 1  # 1-indexed
                # Center the number above the card (9 chars wide)
                num_str = str(card_num)
                padding_before = (9 - len(num_str)) // 2
                padding_after = 9 - len(num_str) - padding_before
                print(" " * padding_before + num_str + " " * padding_after, end="")
            print()
            
            # Print each row of the cards (7 rows tall)
            for j in range(7):
                for card_idx in range(len(row_cards)):
                    card = row_cards[card_idx]
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
                                print("%s" % (card.value), end="")
                            elif len(card.value) > 1 and i % 9 == 2:
                                pass
                            else:
                                print(' ', end='')
                        elif j == 3:
                            if i % 9 == 0 or i % 9 == 8:
                                print("|", end="")
                            elif i % 9 == 4:
                                print("%s" % (suitSymbols[card.suit]), end="")
                            else:
                                print(' ', end='')
                        elif j == 5:
                            if i % 9 == 0 or i % 9 == 8:
                                print("|", end="")
                            elif i % 9 == 7 and len(card.value) > 1:
                                pass
                            elif i % 9 == 7 and len(card.value) == 1:
                                print("%s" % (card.value), end="")
                            elif len(card.value) > 1 and i % 9 == 6:
                                print("%s" % (card.value), end="")
                            else:
                                print(' ', end='')
                        else:
                            if i % 9 == 0 or i % 9 == 8:
                                print('|', end='')
                            else:
                                print(' ', end='')
                print()
            print()  # Extra blank line between rows of cards

class Card:
    # Initializer / Instance Attributes
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    #Pretty print for an individual card
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
                        print("%s" % (suitSymbols[self.suit])  , end="")
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

#A deck is essentially just an empty stack that can be used as various piles in
#different games. To make it a full deck simply add all 52 cards
#TODO should I add a function which automatically initializes a deck with 52 cards?
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

ruleTypes = ["typing", "reverse", "skip"]

#Rule object is used to store all the information relating to each rule
class Rule:
    def __init__(self, triggerValue, triggerSuit, ruleType):
        self.triggerValue = triggerValue
        self.triggerSuit = triggerSuit
        self.ruleType = ruleType
        if ruleType == "typing":
            self.timeToType = input("How long to type out phrase or keyword in seconds?")
            self.phrase = input("What is the phrase to type")
            self.reverse = False
            self.skip = False
        elif ruleType == "reverse":
            self.reverse = True
            self.skip = False
        elif ruleType == "skip":
            self.skip = True
            self.reverse = False
        else:
            print("Error, invalid rule type")

#Wrapper for a dictionary that maps suits to values to rules
class RuleBook:
    def __init__(self):
        self.rules = {}
        for i in range(4):
            cardValues = {
                'all': None,
                'A': None,
                '2': None,
                '3': None,
                '4': None,
                '5': None,
                '6': None,
                '7': None,
                '8': None,
                '9': None,
                '10': None,
                'J': None,
                'Q': None,
                'K': None
            }
        self.rules[suits[i]] = cardValues

    def assignRule(self, suit, value, rule):
        self.rules[suit][value] = rule

    def checkForRule(self, placedCard, prevCard, secondPrevCard):
        pass