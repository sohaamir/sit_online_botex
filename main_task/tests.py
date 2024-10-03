from otree.api import Bot, Submission
from . import *
import random
import time

class PlayerBot(Bot):
    def play_round(self):
        yield Submission(MyPage, check_html=False)
        yield Submission(SecondChoicePage, check_html=False)
        if self.round_number == C.NUM_ROUNDS:
            yield Submission(FinalResults, check_html=False)

    def make_choice(self):
        return random.choice(['left', 'right'])

    def make_bet(self):
        return random.randint(1, 3)

    def live_MyPage(self, data):
        if 'start_choice_phase_timer' in data:
            return dict(choice=self.make_choice())
        elif 'show_bet_container' in data:
            return dict(bet=self.make_bet())

    def live_SecondChoicePage(self, data):
        if 'start_second_choice_timer' in data:
            return dict(second_choice=self.make_choice())
        elif 'show_bet_container' in data:
            return dict(second_bet=self.make_bet())