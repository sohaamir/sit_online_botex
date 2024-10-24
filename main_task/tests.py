from otree.api import Currency as c, currency_range, expect, Bot
from . import *
import random
import time

class PlayerBot(Bot):
    
    def play_round(self):
        # Simulate page load time
        time.sleep(0.1)
        
        # Get the group
        group = self.group
        
        # Set round rewards if not already set
        if not group.field_maybe_none('round_reward_set'):
            group.set_round_reward()
            group.reversal_learning()
        
        # MyPage
        if self.round_number <= C.NUM_ROUNDS:
            # Random choices for first decision
            choice1 = random.choice(['left', 'right'])
            bet1 = random.randint(1, 3)
            
            # Random choices for second decision
            choice2 = random.choice(['left', 'right'])
            bet2 = random.randint(1, 3)
            
            # Submit all choices
            submission = {
                'choice1': choice1,
                'bet1': bet1,
                'choice2': choice2,
                'bet2': bet2,
                'computer_choice1': '',
                'computer_choice2': '',
                'computer_bet_one': False,
                'computer_bet_two': False,
            }
            
            yield MyPage, submission
            
            # Verify that choices were recorded
            player = self.player  # local reference for cleaner code
            
            # Basic field checks using field_maybe_none
            assert player.field_maybe_none('choice1') is not None
            assert player.field_maybe_none('bet1') is not None
            assert player.field_maybe_none('choice2') is not None
            assert player.field_maybe_none('bet2') is not None
            
            # Check chosen images only if they exist
            chosen_image_one = player.field_maybe_none('chosen_image_one')
            if chosen_image_one is not None:
                assert chosen_image_one in C.IMAGES
            
            chosen_image_two = player.field_maybe_none('chosen_image_two')
            if chosen_image_two is not None:
                assert chosen_image_two in C.IMAGES
            
            # Check binary values only if they exist
            chosen_image_one_binary = player.field_maybe_none('chosen_image_one_binary')
            if chosen_image_one_binary is not None:
                assert chosen_image_one_binary in [1, 2]
            
            chosen_image_two_binary = player.field_maybe_none('chosen_image_two_binary')
            if chosen_image_two_binary is not None:
                assert chosen_image_two_binary in [1, 2]
            
            # Check reward and earnings only if they exist
            trial_reward = player.field_maybe_none('trial_reward')
            if trial_reward is not None:
                assert isinstance(trial_reward, (int, float))
            
            choice1_earnings = player.field_maybe_none('choice1_earnings')
            if choice1_earnings is not None:
                assert isinstance(choice1_earnings, (int, float))
            
            choice2_earnings = player.field_maybe_none('choice2_earnings')
            if choice2_earnings is not None:
                assert isinstance(choice2_earnings, (int, float))
            
            # Verify group-level fields
            assert group.field_maybe_none('round_reward_A') is not None
            assert group.field_maybe_none('round_reward_B') is not None
            assert group.field_maybe_none('seventy_percent_image') is not None
        
        # FinalResults
        if self.round_number == C.NUM_ROUNDS:
            yield FinalResults
            
            player = self.player
            
            # Verify final calculations using field_maybe_none
            bonus_payment_score = player.field_maybe_none('bonus_payment_score')
            if bonus_payment_score is not None:
                assert isinstance(bonus_payment_score, (int, float))
            
            base_payoff = player.field_maybe_none('base_payoff')
            if base_payoff is not None:
                assert isinstance(base_payoff, (int, float, c))
            
            bonus_payoff = player.field_maybe_none('bonus_payoff')
            if bonus_payoff is not None:
                assert isinstance(bonus_payoff, (int, float, c))
            
            total_payoff = player.field_maybe_none('total_payoff')
            if total_payoff is not None:
                assert isinstance(total_payoff, (int, float, c))
            
            # Verify the total payoff makes sense if all fields exist
            if all(x is not None for x in [total_payoff, base_payoff, bonus_payoff]):
                assert total_payoff == base_payoff + bonus_payoff
                assert base_payoff == c(6)

def creating_session(subsession):
    if subsession.round_number == 1:
        print("\nStarting bot session...")
        print(f"Number of rounds: {C.NUM_ROUNDS}")
        print(f"Players per group: {C.PLAYERS_PER_GROUP}")
        print("Bot configuration:")
        print("- Making random choices between 'left' and 'right'")
        print("- Making random bets between 1 and 3")
        print("- Testing all stages of each round")
        print("- Verifying calculations and data storage")

class TestCases:
    def test_reversal_sequence(self):
        """Test that reversal sequence is properly generated"""
        sequence, reversal_rounds = generate_trial_sequence()
        assert len(sequence) == C.NUM_ROUNDS
        assert all(isinstance(round_num, int) for round_num, _ in sequence)
        assert all(img in C.IMAGES for _, img in sequence)
        assert all(isinstance(round_num, int) for round_num in reversal_rounds)
    
    def test_reward_sequence(self):
        """Test that reward sequence is properly generated"""
        sequence = generate_reward_sequence(C.NUM_ROUNDS, REVERSAL_ROUNDS)
        assert len(sequence) == C.NUM_ROUNDS
        assert all(isinstance(reward_A, int) and isinstance(reward_B, int) 
                  for reward_A, reward_B in sequence)
        assert all(reward in [0, 1] for rewards in sequence for reward in rewards)
    
    def test_earnings_sequence(self):
        """Test that earnings sequence is properly generated"""
        sequence = generate_earnings_sequence(C.NUM_ROUNDS)
        assert len(sequence) == C.NUM_ROUNDS
        assert all(earning_type in ['choice1_earnings', 'choice2_earnings'] 
                  for earning_type in sequence)