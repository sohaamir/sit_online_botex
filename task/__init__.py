from otree.api import *
import random
import csv
import os

author = 'Aamir Sohail'

doc = """
Script for running a variant of the online Social Influence Task (SIT) adapted to run LLM bots using the `botex` package.

To run this experiment do the following: 

1. Create and activate a virtual environment:

    ```
    python -m venv venv
    source venv/bin/activate  # On Mac/Linux
    ```

2. Install the required packages:

   ` pip install -r requirements.txt`

3. Open a terminal and run an otree server:

    `otree devserver`

4. Open another terminal and run the bot:

   ` python run_botex_experiment.py`


The results will be saved to a folder called `botex_data` for further analysis.
"""

# Constants for the experiment
class C(BaseConstants):
    NAME_IN_URL = 'social_influence_task'
    PLAYERS_PER_GROUP = None  # Each participant is in their own group
    NUM_ROUNDS = 10  # 64 rounds as default (same as the original task)
    
    # Number of virtual players to simulate
    VIRTUAL_PLAYERS = 4
    
    # High probability option for each round (based on your table)
    HIGH_PROBABILITY_OPTION = [
        'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A',  # Rounds 1-16
        'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B',  # Rounds 17-33
        'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A',  # Rounds 34-48
        'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B'  # Rounds 49-64
    ]


# Hardcoded reward sequence for each round: [(A_reward, B_reward), ...]
REWARD_SEQUENCE = [
    (1, 0),  # Round 1
    (1, 0),  # Round 2
    (1, 0),  # Round 3
    (1, 0),  # Round 4
    (0, 1),  # Round 5
    (1, 0),  # Round 6
    (1, 0),  # Round 7
    (1, 0),  # Round 8
    (0, 1),  # Round 9
    (1, 0),  # Round 10
    (1, 0),  # Round 11
    (1, 0),  # Round 12
    (0, 1),  # Round 13
    (1, 0),  # Round 14
    (1, 0),  # Round 15
    (1, 0),  # Round 16
    (0, 1),  # Round 17
    (0, 1),  # Round 18
    (1, 0),  # Round 19
    (0, 1),  # Round 20
    (0, 1),  # Round 21
    (0, 1),  # Round 22
    (1, 0),  # Round 23
    (0, 1),  # Round 24
    (0, 1),  # Round 25
    (0, 1),  # Round 26
    (1, 0),  # Round 27
    (0, 1),  # Round 28
    (0, 1),  # Round 29
    (0, 1),  # Round 30
    (1, 0),  # Round 31
    (0, 1),  # Round 32
    (0, 1),  # Round 33
    (1, 0),  # Round 34
    (1, 0),  # Round 35
    (1, 0),  # Round 36
    (0, 1),  # Round 37
    (1, 0),  # Round 38
    (1, 0),  # Round 39
    (0, 1),  # Round 40
    (1, 0),  # Round 41
    (1, 0),  # Round 42
    (0, 1),  # Round 43
    (1, 0),  # Round 44
    (1, 0),  # Round 45
    (1, 0),  # Round 46
    (0, 1),  # Round 47
    (1, 0),  # Round 48
    (0, 1),  # Round 49
    (1, 0),  # Round 50
    (0, 1),  # Round 51
    (0, 1),  # Round 52
    (0, 1),  # Round 53
    (1, 0),  # Round 54
    (0, 1),  # Round 55
    (0, 1),  # Round 56
    (1, 0),  # Round 57
    (0, 1),  # Round 58
    (0, 1),  # Round 59
    (0, 1),  # Round 60
    (1, 0),  # Round 61
    (0, 1),  # Round 62
    (0, 1),  # Round 63
    (0, 1),  # Round 64
]

# Example responses for the virtual players (59.6% average correct, the actual values are 60.4%)
# These sequences are based on the provided data from the human players, with examples at 20%, 40%, 60% and 80% quartile

# Player 1 sequences (54.7% correct)
p1_choice1 = "AAAABAABBABBABBBAABBBBBBAABABBBAABBBBBBABBAABBABABAAABBBBAAABAAA"
p1_choice2 = "AAAABAABAABBAABBAAABAABBBABBBABBBAAAAAAAABABBAAAABABABBBBAAABABA"

# Player 2 sequences (73.4% correct)
p2_choice1 = "AAAABBAAAAAAAAAAABAABBBBBBBBBBABBAAAAAABAAAAAAAAAAABBBBBAAABBBBB"
p2_choice2 = "AAAABBAAAAAAAAAAABAABBBBBBBBBBABBAAAAAABBAAAAAAAAAABBBBBAAABBBBB"

# Player 3 sequences (47.7% correct)
p3_choice1 = "BAABABAABBBBBAAABABBAAABBBAAAAAAABABBABABAAABBABBAAABABABABAABAB"
p3_choice2 = "ABBAABAABBBABAAABABAABABBBAAAAABBBABAABABAAABAABBAAABABBAAABABBA"

# Player 4 sequences (62.5% correct)
p4_choice1 = "BAAABBAABAAABAAAAAABAAAABBBBBBBBBBBBABBBBBBBAABBBBBBBBBBBBBBBBBB"
p4_choice2 = "AAAABABABAAABAAAAAAAAAAABBBBBBBBAAAABBBBBABBBBBBBBBBBBBBBBBBBBBB"

# Pre-determined choices for virtual players
VIRTUAL_PLAYERS_CHOICE1 = []
for i in range(64):  # 64 rounds
    VIRTUAL_PLAYERS_CHOICE1.append([
        p1_choice1[i], p2_choice1[i], p3_choice1[i], p4_choice1[i]
    ])

# Pre-determined choices for virtual players - Second choice
VIRTUAL_PLAYERS_CHOICE2 = []
for i in range(64):  # 64 rounds
    VIRTUAL_PLAYERS_CHOICE2.append([
        p1_choice2[i], p2_choice2[i], p3_choice2[i], p4_choice2[i]
    ])


class Subsession(BaseSubsession):
    def creating_session(self):
        pass  # No need for group management since PLAYERS_PER_GROUP = None


class Group(BaseGroup):
    # Reward outcomes for the current round
    round_reward_A = models.IntegerField()             # Reward for option A in current round (1 or 0)
    round_reward_B = models.IntegerField()             # Reward for option B in current round (1 or 0)
    
    # Probability settings for the two options
    high_probability_option = models.StringField()     # Which option ('A' or 'B') has high probability in this round
    
    def set_round_rewards(self):
        """Set the rewards for options A and B in the current round"""
        # Get rewards from the pre-generated sequence
        self.round_reward_A, self.round_reward_B = REWARD_SEQUENCE[self.round_number - 1]
        
        # Set which option has high probability in this round
        self.high_probability_option = C.HIGH_PROBABILITY_OPTION[self.round_number - 1]
        
        print(f"Round {self.round_number}: Option {self.high_probability_option} has high probability")
        print(f"Rewards: A = {self.round_reward_A}, B = {self.round_reward_B}")


class Player(BasePlayer):
    # Comprehension check fields
    q1_correct = models.BooleanField(initial=False)
    q2_correct = models.BooleanField(initial=False)
    q3_correct = models.BooleanField(initial=False)
    q4_correct = models.BooleanField(initial=False)

    # Comprehension check fields
    comprehension_q1 = models.StringField(
        choices=[
            ['40 points', '40 points'],
            ['minus 40 points', 'minus 40 points'],
            ['60 points', '60 points'],
            ['minus 60 points', 'minus 60 points']
        ],
        widget=widgets.RadioSelect
    )
    
    comprehension_q2 = models.StringField(
        choices=[
            ['Option 1', 'Option 1'],
            ['Option 2', 'Option 2'],
            ['Option 3', 'Option 3'],
            ['Option 4', 'Option 4']
        ],
        widget=widgets.RadioSelect
    )
    
    comprehension_q3 = models.StringField(
        choices=[
            ['From your initial choice and bet only', 'From your initial choice and bet only'],
            ['From your second bet and choice only', 'From your second bet and choice only'],
            ['From either the first and second choices/bets but randomly on each trial', 'From either the first and second choices/bets but randomly on each trial'],
            ['From both the first and second choices/bets on each trial', 'From both the first and second choices/bets on each trial']
        ],
        widget=widgets.RadioSelect
    )
    
    comprehension_q4 = models.StringField(
        choices=[
            ['Randomly determined', 'Randomly determined'],
            ['One option will give you a reward everytime, and the other will give you a loss everytime', 'One option will give you a reward everytime, and the other will give you a loss everytime'],
            ['One option will give you a reward randomly, and the other will give you a loss randomly', 'One option will give you a reward randomly, and the other will give you a loss randomly'],
            ['One option will give you a reward most of the time, and the other will give you a loss most of the time', 'One option will give you a reward most of the time, and the other will give you a loss most of the time']
        ],
        widget=widgets.RadioSelect
    )
    
    # Fields to track correctness
    q1_correct = models.BooleanField(initial=False)
    q2_correct = models.BooleanField(initial=False)
    q3_correct = models.BooleanField(initial=False)
    q4_correct = models.BooleanField(initial=False)

    # Choice and bet tracking variables
    choice1 = models.StringField(widget=widgets.RadioSelect, choices=['A', 'B'])     # Player's first choice ('A' or 'B')
    choice2 = models.StringField(widget=widgets.RadioSelect, choices=['A', 'B'])     # Player's second choice ('A' or 'B')
    bet1 = models.IntegerField(widget=widgets.RadioSelect, choices=[1, 2, 3])       # Amount bet on first choice (1-3)
    bet2 = models.IntegerField(widget=widgets.RadioSelect, choices=[1, 2, 3])       # Amount bet on second choice (1-3)
    trial_reward = models.IntegerField(initial=0)        # Reward received in current trial (1 or 0)
    
    # Social influence tracking - as percentages (decimals)
    choice1_with = models.FloatField(initial=0)        # Percentage of others who made same first choice
    choice1_against = models.FloatField(initial=0)     # Percentage of others who made different first choice
    choice2_with = models.FloatField(initial=0)        # Percentage of others who made same second choice
    choice2_against = models.FloatField(initial=0)     # Percentage of others who made different second choice
    
    # Performance metrics
    choice1_accuracy = models.BooleanField(initial=0)    # Whether first choice was optimal
    choice2_accuracy = models.BooleanField(initial=0)    # Whether second choice was optimal
    choice1_accuracy_sum = models.IntegerField(initial=0)# Sum choice1 accuracy over trials
    choice2_accuracy_sum = models.IntegerField(initial=0)# Sum choice2 accuracy over trials
    switch_vs_stay = models.IntegerField()               # Whether player switched (1) or stayed (0) between choices

    # Binary reward tracking
    choice1_reward_binary = models.IntegerField(initial=0)  # Whether first choice was rewarded (1) or not (0)
    choice2_reward_binary = models.IntegerField(initial=0)  # Whether second choice was rewarded (1) or not (0)
    
    # Earnings tracking
    choice1_earnings = models.IntegerField(initial=0)     # Points earned from first choice
    choice2_earnings = models.IntegerField(initial=0)     # Points earned from second choice
    bonus_payment_score = models.IntegerField(initial=0)  # Total bonus points earned
    
    # Outcome tracking
    loss_or_gain = models.IntegerField()                  # Whether player gained (1) or lost (-1) points
    
    # Virtual players' choices - First choice
    player1_choice_one = models.StringField()
    player2_choice_one = models.StringField()
    player3_choice_one = models.StringField()
    player4_choice_one = models.StringField()
    
    # Virtual players' choices - Second choice
    player1_choice_two = models.StringField()
    player2_choice_two = models.StringField()
    player3_choice_two = models.StringField()
    player4_choice_two = models.StringField()
    
    # Track accuracy of virtual players' choices - First choice
    player1_choice1_accuracy = models.BooleanField()
    player2_choice1_accuracy = models.BooleanField()
    player3_choice1_accuracy = models.BooleanField()
    player4_choice1_accuracy = models.BooleanField()
    
    # Track accuracy of virtual players' choices - Second choice
    player1_choice2_accuracy = models.BooleanField()
    player2_choice2_accuracy = models.BooleanField()
    player3_choice2_accuracy = models.BooleanField()
    player4_choice2_accuracy = models.BooleanField()
    
    # Track whether virtual players gained or lost points
    player1_loss_or_gain = models.IntegerField()
    player2_loss_or_gain = models.IntegerField()
    player3_loss_or_gain = models.IntegerField()
    player4_loss_or_gain = models.IntegerField()
    
    def set_virtual_players_choices_and_outcomes(self):
        """Set the choices and outcomes for virtual players based on pre-determined sequences"""
        round_index = self.round_number - 1
        
        # Set first choices for virtual players
        self.player1_choice_one = VIRTUAL_PLAYERS_CHOICE1[round_index][0]
        self.player2_choice_one = VIRTUAL_PLAYERS_CHOICE1[round_index][1]
        self.player3_choice_one = VIRTUAL_PLAYERS_CHOICE1[round_index][2]
        self.player4_choice_one = VIRTUAL_PLAYERS_CHOICE1[round_index][3]
        
        # Set second choices for virtual players
        self.player1_choice_two = VIRTUAL_PLAYERS_CHOICE2[round_index][0]
        self.player2_choice_two = VIRTUAL_PLAYERS_CHOICE2[round_index][1]
        self.player3_choice_two = VIRTUAL_PLAYERS_CHOICE2[round_index][2]
        self.player4_choice_two = VIRTUAL_PLAYERS_CHOICE2[round_index][3]
        
        # Calculate accuracy for first choices
        high_prob_option = self.group.high_probability_option
        self.player1_choice1_accuracy = (self.player1_choice_one == high_prob_option)
        self.player2_choice1_accuracy = (self.player2_choice_one == high_prob_option)
        self.player3_choice1_accuracy = (self.player3_choice_one == high_prob_option)
        self.player4_choice1_accuracy = (self.player4_choice_one == high_prob_option)
        
        # Calculate accuracy for second choices
        self.player1_choice2_accuracy = (self.player1_choice_two == high_prob_option)
        self.player2_choice2_accuracy = (self.player2_choice_two == high_prob_option)
        self.player3_choice2_accuracy = (self.player3_choice_two == high_prob_option)
        self.player4_choice2_accuracy = (self.player4_choice_two == high_prob_option)
        
        # Calculate reward outcomes for virtual players
        if self.player1_choice_two == 'A':
            p1_rewarded = self.group.round_reward_A == 1
        else:
            p1_rewarded = self.group.round_reward_B == 1
            
        if self.player2_choice_two == 'A':
            p2_rewarded = self.group.round_reward_A == 1
        else:
            p2_rewarded = self.group.round_reward_B == 1
            
        if self.player3_choice_two == 'A':
            p3_rewarded = self.group.round_reward_A == 1
        else:
            p3_rewarded = self.group.round_reward_B == 1
            
        if self.player4_choice_two == 'A':
            p4_rewarded = self.group.round_reward_A == 1
        else:
            p4_rewarded = self.group.round_reward_B == 1
        
        # Set gain/loss values (1 for gain, -1 for loss)
        self.player1_loss_or_gain = 1 if p1_rewarded else -1
        self.player2_loss_or_gain = 1 if p2_rewarded else -1
        self.player3_loss_or_gain = 1 if p3_rewarded else -1
        self.player4_loss_or_gain = 1 if p4_rewarded else -1
    
    def calculate_first_choice_social_influence(self):
        """Calculate the percentage of others who made same/different first choices"""
        # First choice agreement
        same_choice1 = 0
        for choice in [self.player1_choice_one, self.player2_choice_one,
                    self.player3_choice_one, self.player4_choice_one]:
            if choice == self.choice1:
                same_choice1 += 1
        
        self.choice1_with = same_choice1 / C.VIRTUAL_PLAYERS
        self.choice1_against = 1 - self.choice1_with

    def calculate_second_choice_social_influence(self):
        """Calculate the percentage of others who made same/different second choices"""
        # Second choice agreement
        same_choice2 = 0
        for choice in [self.player1_choice_two, self.player2_choice_two,
                    self.player3_choice_two, self.player4_choice_two]:
            if choice == self.choice2:
                same_choice2 += 1
        
        self.choice2_with = same_choice2 / C.VIRTUAL_PLAYERS
        self.choice2_against = 1 - self.choice2_with
    
    def calculate_choice1_earnings(self):
        """Calculate earnings for first choice"""
        # For choice1, we need to see if it would have been rewarded
        if self.choice1 == 'A':
            choice1_reward = self.group.round_reward_A
        else:  # 'B'
            choice1_reward = self.group.round_reward_B
            
        if choice1_reward == 1:  # Would have been rewarded
            self.choice1_earnings = self.bet1 * 20  # Positive points
        else:  # Would not have been rewarded
            self.choice1_earnings = -1 * self.bet1 * 20  # Negative points
            
        self.choice1_reward_binary = choice1_reward
    
    def update_accuracy_sums(self):
        """Update the cumulative accuracy sums across rounds"""
        if self.round_number == 1:
            self.choice1_accuracy_sum = int(self.choice1_accuracy)
            self.choice2_accuracy_sum = int(self.choice2_accuracy)
        else:
            previous_player = self.in_round(self.round_number - 1)
            self.choice1_accuracy_sum = previous_player.choice1_accuracy_sum + int(self.choice1_accuracy)
            self.choice2_accuracy_sum = previous_player.choice2_accuracy_sum + int(self.choice2_accuracy)

class Welcome(Page):
    """Initial page with study information and consent"""
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

class TaskStructure(Page):
    """Reward structure page"""
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

class RoundStructure(Page):
    """Task RoundStructure page"""
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

class Comprehension(Page):
    form_model = 'player'
    form_fields = ['comprehension_q1', 'comprehension_q2', 'comprehension_q3', 'comprehension_q4']
    
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Check each answer and store correctness
        player.q1_correct = player.comprehension_q1 == 'minus 60 points'
        player.q2_correct = player.comprehension_q2 == 'Option 3'
        player.q3_correct = player.comprehension_q3 == 'From either the first and second choices/bets but randomly on each trial'
        player.q4_correct = player.comprehension_q4 == 'One option will give you a reward most of the time, and the other will give you a loss most of the time'
    
    # We don't stop the bot from progressing regardless of answers
    def error_message(self, values):
        return None
        
class ComprehensionResults(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        return {
            'q1_correct': player.q1_correct,
            'q2_correct': player.q2_correct,
            'q3_correct': player.q3_correct,
            'q4_correct': player.q4_correct,
            'q1_answer': player.comprehension_q1,
            'q2_answer': player.comprehension_q2,
            'q3_answer': player.comprehension_q3,
            'q4_answer': player.comprehension_q4,
            'all_correct': player.q1_correct and player.q2_correct and 
                          player.q3_correct and player.q4_correct
        }

class Transition(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

class FirstDecisions(Page):
    form_model = 'player'
    form_fields = ['choice1', 'bet1']
    
    @staticmethod
    def vars_for_template(player):
        # Ensure group rewards are set for this round
        player.group.set_round_rewards()
        
        # Set up virtual players
        player.set_virtual_players_choices_and_outcomes()
        
        return {
            'round_number': player.round_number,
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Calculate agreement with other players for first choice only
        player.calculate_first_choice_social_influence()


class SecondDecisions(Page):
    form_model = 'player'
    form_fields = ['choice2', 'bet2']
    
    @staticmethod
    def vars_for_template(player):
        return {
            'round_number': player.round_number,
            'choice1': player.choice1,
            'bet1': player.bet1,
            'player1_choice': player.player1_choice_one,
            'player2_choice': player.player2_choice_one,
            'player3_choice': player.player3_choice_one,
            'player4_choice': player.player4_choice_one,
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Calculate earnings for first choice (not shown to player)
        player.calculate_choice1_earnings()
        
        # Calculate rewards for second choice
        if player.choice2 == 'A':
            player.trial_reward = player.group.round_reward_A
        else:  # 'B'
            player.trial_reward = player.group.round_reward_B
        
        # Calculate second choice earnings
        if player.trial_reward == 1:  # Option was rewarded
            player.choice2_earnings = player.bet2 * 20  # Positive points
        else:  # Option was not rewarded
            player.choice2_earnings = -1 * player.bet2 * 20  # Negative points
            
        # Update cumulative score
        if player.round_number == 1:
            player.bonus_payment_score = player.choice2_earnings
        else:
            prev_player = player.in_round(player.round_number - 1)
            player.bonus_payment_score = prev_player.bonus_payment_score + player.choice2_earnings
        
        # Set whether the player gained or lost points
        player.loss_or_gain = 1 if player.choice2_earnings > 0 else -1
        
        # Update accuracy metrics
        player.choice1_accuracy = (player.choice1 == player.group.high_probability_option)
        player.choice2_accuracy = (player.choice2 == player.group.high_probability_option)
        
        # Update accuracy sums
        player.update_accuracy_sums()
        
        # Calculate if player switched or stayed
        player.switch_vs_stay = 1 if player.choice1 != player.choice2 else 0
        
        # Record whether second choice was rewarded
        player.choice2_reward_binary = player.trial_reward
        
        # Calculate agreement with other players for second choice
        player.calculate_second_choice_social_influence()


class RoundResults(Page):
    @staticmethod
    def vars_for_template(player):
        # Calculate the absolute value of points earned for display
        points_display = abs(player.choice2_earnings)
        
        # Create outcome displays for virtual players
        player1_outcome = "Correct" if player.player1_loss_or_gain == 1 else "Incorrect"
        player2_outcome = "Correct" if player.player2_loss_or_gain == 1 else "Incorrect" 
        player3_outcome = "Correct" if player.player3_loss_or_gain == 1 else "Incorrect"
        player4_outcome = "Correct" if player.player4_loss_or_gain == 1 else "Incorrect"
        
        return {
            'round_number': player.round_number,
            'choice2': player.choice2,
            'choice_outcome': "correct" if player.trial_reward == 1 else "incorrect",
            'points_earned': player.choice2_earnings,
            'points_display': points_display,
            'total_points': player.bonus_payment_score,
            
            # Virtual players' choices and outcomes
            'player1_choice': player.player1_choice_two,
            'player2_choice': player.player2_choice_two,
            'player3_choice': player.player3_choice_two,
            'player4_choice': player.player4_choice_two,
            'player1_outcome': player1_outcome,
            'player2_outcome': player2_outcome,
            'player3_outcome': player3_outcome,
            'player4_outcome': player4_outcome,
        }


class FinalResults(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS
    
    @staticmethod
    def vars_for_template(player):
        return {
            'bonus_payment_score': player.bonus_payment_score,
            'bonus_payoff': cu(max(0, player.bonus_payment_score / 600)),
        }


page_sequence = [Welcome, TaskStructure, RoundStructure, Comprehension, ComprehensionResults, Transition, FirstDecisions, SecondDecisions, RoundResults, FinalResults]