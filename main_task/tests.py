from otree.api import Bot, Submission, expect
from . import *
import random
import time

class PlayerBot(Bot):
    def make_random_choice(self):
        return random.choice(['left', 'right'])

    def make_random_bet(self):
        return random.randint(1, 3)

    def call_live_method(self, method):
        # Initial choice
        choice = self.make_random_choice()
        method(self.player.id_in_group, {'choice': choice, 'initial_choice_time': 1500})

        # Initial bet
        bet = self.make_random_bet()
        method(self.player.id_in_group, {'bet': bet, 'initial_bet_time': 1500})

        # Second choice
        second_choice = self.make_random_choice()
        method(self.player.id_in_group, {'second_choice': second_choice, 'second_choice_time': 1500})

        # Second bet
        second_bet = self.make_random_bet()
        method(self.player.id_in_group, {'second_bet': second_bet, 'second_bet_time': 1500})

    def play_round(self):
        # MyPage
        yield MyPage, dict(choice1=self.make_random_choice(), bet1=self.make_random_bet())

        # SecondChoicePage
        yield SecondChoicePage, dict(choice2=self.make_random_choice(), bet2=self.make_random_bet())

        # FinalResults
        yield FinalResults

def call_live_method(method, **kwargs):
    bot = PlayerBot(None)
    bot.call_live_method(method)