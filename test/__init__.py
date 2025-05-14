from otree.api import *
import random

author = 'Aamir Sohail'

doc = """
A simple reversal learning task with two options (A and B).
On each trial, one option is correct (rewarded) and one is incorrect (not rewarded).
The correct option switches every 8-12 trials without warning.
Option B starts as the correct option.
"""

# Constants for the experiment
class C(BaseConstants):
    NAME_IN_URL = 'test'
    PLAYERS_PER_GROUP = None  # Individual task
    NUM_ROUNDS = 10  # Shorter than the original task

# Function to generate reversal points
def generate_reversal_points(num_rounds):
    reversal_points = []
    current_point = 0
    
    while current_point < num_rounds:
        # Add a reversal point every 8-12 trials
        reversal_interval = random.randint(8, 12)
        current_point += reversal_interval
        
        # Make sure we don't exceed the number of rounds
        if current_point < num_rounds:
            reversal_points.append(current_point)
    
    return reversal_points

# Generate correct options for all rounds
def generate_correct_options(reversal_points, num_rounds):
    correct_options = []
    # Start with B as the correct option
    correct_option = 'B'
    
    for round_num in range(1, num_rounds + 1):
        # Check if we've reached a reversal point
        if round_num in reversal_points:
            # Switch the correct option
            correct_option = 'A' if correct_option == 'B' else 'B'
        
        # Store the correct option for this round
        correct_options.append(correct_option)
    
    return correct_options

class Subsession(BaseSubsession):
    def creating_session(self):
        # Only do this once for the entire session
        if self.round_number == 1:
            # Generate reversal points
            reversal_points = generate_reversal_points(C.NUM_ROUNDS)
            # Generate the sequence of correct options
            correct_options = generate_correct_options(reversal_points, C.NUM_ROUNDS)
            
            # Store in session vars
            self.session.vars['reversal_points'] = reversal_points
            self.session.vars['correct_options'] = correct_options
            
            print(f"Initialized session variables:")
            print(f"Reversal points: {reversal_points}")
            print(f"Correct options: {correct_options}")

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    choice = models.StringField(
        choices=['A', 'B'],
        widget=widgets.RadioSelect,
        label="Which option do you choose?"
    )
    
    is_correct = models.BooleanField()  # Whether the player's choice was correct
    score = models.IntegerField(initial=0)  # Player's score for this round (1=correct, 0=incorrect)
    total_score = models.IntegerField(initial=0)  # Cumulative score
    
    # Store the correct option for this round
    correct_option = models.StringField()

    def determine_outcome(self):
        try:
            # Get the correct option from session vars
            if 'correct_options' in self.session.vars:
                self.correct_option = self.session.vars['correct_options'][self.round_number - 1]
            else:
                # Fallback if session vars not available - default to B for even rounds, A for odd
                self.correct_option = 'B' if self.round_number % 2 == 0 else 'A'
                print(f"WARNING: Using fallback for correct option in round {self.round_number}")
            
            # Determine if the player's choice is correct
            self.is_correct = (self.choice == self.correct_option)
            
            # Calculate score for this round (1 if correct, 0 if incorrect)
            self.score = 1 if self.is_correct else 0
            
            # Update total score
            if self.round_number == 1:
                self.total_score = self.score
            else:
                prev_player = self.in_round(self.round_number - 1)
                self.total_score = prev_player.total_score + self.score
                
            print(f"Round {self.round_number}: Correct option is {self.correct_option}, player chose {self.choice}")
            print(f"Correct: {self.is_correct}, Score: {self.score}")
            
        except Exception as e:
            print(f"Error in determine_outcome: {e}")
            # Set safe defaults to avoid crashing
            self.is_correct = False
            self.score = 0
            if self.round_number > 1:
                prev_player = self.in_round(self.round_number - 1)
                self.total_score = prev_player.total_score
            else:
                self.total_score = 0

class Instructions(Page):
    """Instructions for the task"""
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Double-check that session variables are initialized
        if 'correct_options' not in player.session.vars:
            print("Session variables not initialized yet, doing it now")
            reversal_points = generate_reversal_points(C.NUM_ROUNDS)
            correct_options = generate_correct_options(reversal_points, C.NUM_ROUNDS)
            player.session.vars['reversal_points'] = reversal_points
            player.session.vars['correct_options'] = correct_options

class Decision(Page):
    """Player makes a choice between options A and B"""
    form_model = 'player'
    form_fields = ['choice']
    
    @staticmethod
    def vars_for_template(player):
        if player.round_number > 1:
            prev_player = player.in_round(player.round_number - 1)
            return {'prev_player': prev_player}
        return {}
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Determine outcome based on player's choice
        player.determine_outcome()

class Result(Page):
    """Show the outcome of the player's choice"""
    
    @staticmethod
    def vars_for_template(player):
        return {
            'round_number': player.round_number,
            'choice': player.choice,
            'is_correct': player.is_correct,
            'score': player.score,
            'total_score': player.total_score
        }

class FinalResult(Page):
    """Show final results at the end of the task"""
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS
    
    @staticmethod
    def vars_for_template(player):
        percent_score = (player.total_score / C.NUM_ROUNDS) * 100
        return {
            'total_score': player.total_score,
            'num_rounds': C.NUM_ROUNDS,
            'percent_score': percent_score
        }

page_sequence = [Instructions, Decision, Result, FinalResult]