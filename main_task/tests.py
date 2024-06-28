from otree.api import Bot, Submission
from . import *
import random

class PlayerBot(Bot):

    def play_round(self):
        print(f"\n--- Starting Round {self.round_number} for Player {self.player.id_in_group} ---")

        yield Submission(MyPage, check_html=False)
        
        self.player.chosen_image_one = random.choice(C.IMAGES)
        
        print(f"Round {self.round_number}, Player {self.player.id_in_group}:")
        print(f"Initial choice: {self.player.choice1}")
        print(f"Chosen image one: {self.player.chosen_image_one}")
        print(f"Initial bet: {self.player.bet1}")
        print(f"Preference choices: {self.player.preference_choice}, {self.player.preference_second_choice}")
        
        yield Submission(SecondChoicePage, {
            'choice2': self._random_choice(),
            'bet2': self._random_bet()
        }, check_html=False)
        
        print(f"Second choice: {self.player.choice2}")
        print(f"Second bet: {self.player.bet2}")
        
        if self.round_number == C.NUM_ROUNDS:
            yield Submission(FinalResults, check_html=False)
            bot_data = self.subsession.collect_bot_data()
            print("\n--- Final Bot Data ---")
            for round_data in bot_data:
                print(round_data)

    def _random_response_time(self):
        return random.randint(500, 3900)  # Random time between 500ms and 3900ms

    def _random_choice(self):
        return random.choice(['left', 'right'])

    def _random_bet(self):
        return random.randint(1, 3)

    def _random_preference(self):
        return str(random.randint(1, 2))

    def _random_image(self):
        return random.choice(C.IMAGES)

    def live_MyPage(self, data):
        if 'start_choice_phase_timer' in data:
            choice = self._random_choice()
            chosen_image = self.player.left_image if choice == 'left' else self.player.right_image
            self.player.chosen_image_one = chosen_image
            self.player.choice1 = choice
            yield {
                'initial_choice_time': self._random_response_time(),
                'choice': choice
            }
        elif 'show_bet_container' in data:
            bet = self._random_bet()
            self.player.bet1 = bet
            yield {
                'initial_bet_time': self._random_response_time(),
                'bet': bet
            }
        elif 'show_preference_choice' in data:
            preference = self._random_preference()
            self.player.preference_choice = preference
            yield {
                'preference_choice': preference,
                'preference_choice_time': self._random_response_time()
            }
        elif 'show_preference_second_choice' in data:
            second_pref = self._random_preference()
            while second_pref == self.player.field_maybe_none('preference_choice'):
                second_pref = self._random_preference()
            self.player.preference_second_choice = second_pref
            yield {
                'preference_second_choice': second_pref,
                'preference_second_choice_time': self._random_response_time()
            }

    def live_SecondChoicePage(self, data):
        if 'start_second_choice_timer' in data:
            choice = self._random_choice()
            chosen_image = self.player.left_image if choice == 'left' else self.player.right_image
            self.player.chosen_image_two = chosen_image
            self.player.choice2 = choice
            yield {
                'second_choice': choice,
                'second_choice_time': self._random_response_time()
            }
        elif 'show_bet_container' in data:
            bet = self._random_bet()
            self.player.bet2 = bet
            yield {
                'second_bet': bet,
                'second_bet_time': self._random_response_time()
            }