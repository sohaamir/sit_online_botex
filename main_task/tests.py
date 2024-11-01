# tests.py
from otree.api import Bot, Submission, expect
import random
import time
import logging
from . import MyPage, FinalResults, C

class PlayerBot(Bot):
    def play_round(self):
        logging.info(f"Bot starting round {self.round_number} for player {self.player.id_in_group}")
        
        # First phase - Page load and initial choice
        yield Submission(MyPage, {
            'my_page_load_time': time.time() * 1000,
            'individual_page_load_time': time.time() * 1000,
            'choice1': random.choice(['left', 'right']),
            'initial_choice_time': random.randint(1000, 2500),  # Random response time between 1-2.5s
            'choice_phase_timer_ended': True
        }, timeout_happened=False)

        # First bet phase
        yield Submission(MyPage, {
            'bet': random.randint(1, 3),
            'initial_bet_time': random.randint(1000, 2500),
            'bet_timer_ended': True,
            'show_bet_container': True
        }, timeout_happened=False)

        # Display phase
        yield Submission(MyPage, {
            'display_all_images': True,
            'start_display_timer': True
        }, timeout_happened=False)

        time.sleep(4)  # Wait for display phase

        # Second choice phase
        yield Submission(MyPage, {
            'second_choice': random.choice(['left', 'right']),
            'second_choice_time': random.randint(1000, 2500),
            'manual_second_choice': True,
            'second_choice_timer_ended': True
        }, timeout_happened=False)

        # Second bet phase
        yield Submission(MyPage, {
            'second_bet': random.randint(1, 3),
            'second_bet_time': random.randint(1000, 2500),
            'second_bet_timer_ended': True
        }, timeout_happened=False)

        # Handle final round
        if self.round_number == C.NUM_ROUNDS:
            logging.info(f"Bot {self.player.id_in_group} completing final round")
            yield Submission(FinalResults, check_html=False)

    def validate_play(self):
        """Validate that the bot made all required choices and bets"""
        if self.round_number < C.NUM_ROUNDS:
            expect(self.player.choice1, '!=', None)
            expect(self.player.bet1, '>', 0)
            expect(self.player.choice2, '!=', None)
            expect(self.player.bet2, '>', 0)