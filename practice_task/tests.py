# practice_task/tests.py

from otree.api import Bot, Submission, expect
import random
import time
import logging
from . import MyPage, FinalResults, WaitPage1, TransitionToPracticeTask, C, MainTaskInstructions

class PlayerBot(Bot):
    def play_round(self):
        logging.info(f"Bot starting round {self.round_number} for player {self.player.id_in_group}")

        # Handle WaitPage1 and TransitionToPracticeTask only in round 1
        if self.round_number == 1:
            yield Submission(TransitionToPracticeTask, check_html=False)
        
        # Initialize left/right images
        if not self.player.field_maybe_none('left_image'):
            images = C.IMAGES.copy()
            random.shuffle(images)
            self.player.left_image = images[0]
            self.player.right_image = images[1]

        # Make first choice and set chosen image
        choice1 = random.choice(['left', 'right'])
        chosen_image_one = self.player.left_image if choice1 == 'left' else self.player.right_image
        bet1 = random.randint(1, 3)

        # Make second choice and set chosen image
        choice2 = random.choice(['left', 'right'])
        chosen_image_two = self.player.left_image if choice2 == 'left' else self.player.right_image
        bet2 = random.randint(1, 3)

        # Submit all choices and bets together
        submission_data = {
            'choice1': choice1,
            'bet1': bet1,
            'choice2': choice2,
            'bet2': bet2,
        }

        # Set the chosen images explicitly
        self.player.chosen_image_one = chosen_image_one
        self.player.chosen_image_two = chosen_image_two
        
        # Initialize group rewards if not already set (only player 1 does this)
        if self.player.id_in_group == 1:
            if not self.group.field_maybe_none('round_reward_set'):
                self.group.set_round_reward()
                self.group.reversal_learning()
                reward_a, reward_b = C.REWARD_SEQUENCE[self.round_number - 1]
                self.group.round_reward_A = reward_a
                self.group.round_reward_B = reward_b
                self.group.round_reward_set = True

        # Submit the form with all required fields
        yield Submission(MyPage, submission_data, timeout_happened=False, check_html=False)

        # Only show final results on last round
        if self.round_number == C.NUM_ROUNDS:
            yield Submission(FinalResults, check_html=False)
            yield Submission(MainTaskInstructions, check_html=False)

    def validate_play(self):
        """Validate that the bot made all required choices and bets"""
        if self.round_number < C.NUM_ROUNDS:
            expect(self.player.field_maybe_none('choice1') in ['left', 'right'])
            expect(self.player.field_maybe_none('bet1') in [1, 2, 3])
            expect(self.player.field_maybe_none('choice2') in ['left', 'right'])
            expect(self.player.field_maybe_none('bet2') in [1, 2, 3])
            expect(self.player.field_maybe_none('chosen_image_one') is not None)
            expect(self.player.field_maybe_none('chosen_image_two') is not None)