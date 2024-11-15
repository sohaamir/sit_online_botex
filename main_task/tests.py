# main_task/__init__.py:

from otree.api import Bot, Submission, expect
import random
import time
import logging
from . import MyPage, FinalResults, WaitPage2, TransitionToMainTask, C

class PlayerBot(Bot):
    def play_round(self):
        logging.info(f"Bot starting round {self.round_number} for player {self.player.id_in_group}")
        
        try:
            # Handle WaitPage2 and TransitionToMainTask only in round 1
            if self.round_number == 1:
                yield Submission(TransitionToMainTask, check_html=False)

            # Initialize group rewards if needed (only player 1 does this)
            if self.player.id_in_group == 1:
                # Get rewards from pre-generated sequence
                reward_a, reward_b = C.REWARD_SEQUENCE[self.round_number - 1]
                self.group.round_reward_A = reward_a
                self.group.round_reward_B = reward_b
                self.group.round_reward_set = True
                
                # Handle reversals AFTER setting rewards
                self.group.reversal_learning()
                
                logging.info(f"Round {self.round_number} rewards set: "
                           f"A={self.group.round_reward_A}, "
                           f"B={self.group.round_reward_B}")

            # Wait for player 1 to set rewards
            time.sleep(0.2)
            
            # Initialize images
            images = C.IMAGES.copy()
            random.shuffle(images)
            self.player.left_image = images[0]
            self.player.right_image = images[1]
            
            # Make choices and bets
            choice1 = random.choice(['left', 'right'])
            choice2 = random.choice(['left', 'right'])
            bet1 = random.randint(1, 3)
            bet2 = random.randint(1, 3)
            
            # Set chosen images
            self.player.chosen_image_one = self.player.left_image if choice1 == 'left' else self.player.right_image
            self.player.chosen_image_two = self.player.left_image if choice2 == 'left' else self.player.right_image
            
            # Set choices
            self.player.choice1 = choice1
            self.player.choice2 = choice2
            self.player.bet1 = bet1
            self.player.bet2 = bet2

            # Submit page
            yield Submission(MyPage, {
                'choice1': choice1,
                'bet1': bet1,
                'choice2': choice2,
                'bet2': bet2,
            }, timeout_happened=False, check_html=False)

            # Wait for all players to finish
            if self.player.id_in_group == len(self.group.get_players()):
                self.group.set_payoffs()
                time.sleep(0.2)

            # Only yield FinalResults on last round
            if self.round_number == C.NUM_ROUNDS:
                yield Submission(FinalResults, check_html=False)

        except Exception as e:
            logging.error(f"Error in bot round {self.round_number} for player {self.player.id_in_group}: {e}")
            raise

    def validate_play(self):
        """Validate that the bot made all required choices and bets"""
        try:
            if self.round_number < C.NUM_ROUNDS:
                # Use field_maybe_none for all field access
                group_reward_a = self.group.field_maybe_none('round_reward_A')
                group_reward_b = self.group.field_maybe_none('round_reward_B')
                
                # Validate rewards are set
                expect(group_reward_a is not None, 'round_reward_A should not be None')
                expect(group_reward_b is not None, 'round_reward_B should not be None')
                
                # Validate player fields are set
                expect(self.player.field_maybe_none('choice1') in ['left', 'right'])
                expect(self.player.field_maybe_none('bet1') in [1, 2, 3])
                expect(self.player.field_maybe_none('choice2') in ['left', 'right'])
                expect(self.player.field_maybe_none('bet2') in [1, 2, 3])
                
                # Validate images are set
                chosen_one = self.player.field_maybe_none('chosen_image_one')
                chosen_two = self.player.field_maybe_none('chosen_image_two')
                
                expect(chosen_one is not None, 'chosen_image_one should not be None')
                expect(chosen_two is not None, 'chosen_image_two should not be None')
                expect(chosen_one in C.IMAGES, f'chosen_image_one should be in {C.IMAGES}')
                expect(chosen_two in C.IMAGES, f'chosen_image_two should be in {C.IMAGES}')

        except Exception as e:
            logging.error(f"Error validating bot play for player {self.player.id_in_group}: {e}")
            raise