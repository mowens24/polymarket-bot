# risk/position_sizing.py - Easy to extend later

from config import MAX_BET_USD


def fixed_sizing():
    return MAX_BET_USD


# Future: add kelly_sizing(client), percent_of_balance(client, percent=0.2), etc.
