# -------------------------------------------------------------------------------------------------------------------- #
# --------------- IMPORTS: IMPORT ALL NECESSARY MODULES AND LIBRARIES REQUIRED FOR THE GAME ----------------- #
# -------------------------------------------------------------------------------------------------------------------- #

from django.db.models import Prefetch
from otree.models import BasePlayer
from django.db import connection
from otree.api import *
import threading
from . import *
import logging
import random
import time
import csv
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Add after your imports
TOTAL_QUERIES = 0

def log_query_count(action_name, round_number=None):
    """Debug function to log number of database queries"""
    global TOTAL_QUERIES
    query_count = len(connection.queries)
    current_queries = query_count - TOTAL_QUERIES
    TOTAL_QUERIES = query_count
    
    if round_number:
        print(f"Round {round_number} - {action_name}: {current_queries} queries (Total: {TOTAL_QUERIES})")
    else:
        print(f"{action_name}: {current_queries} queries (Total: {TOTAL_QUERIES})")
    
    return query_count

# -------------------------------------------------------------------------------------------------------------------- #
# --------------- AUTHORSHIP INFORMATION: DEFINE THE AUTHOR AND DOCUMENTATION FOR THE GAME ----------------- #
# -------------------------------------------------------------------------------------------------------------------- #

author = 'Aamir Sohail'

doc = """
This is a multiplayer social influence task where players in groups of 5 make choices and bets to earn rewards in real time. 
The task is the same as reported in (Zhang & Glascher, 2020) https://www.science.org/doi/full/10.1126/sciadv.abb4159
"""

# -------------------------------------------------------------------------------------------------------------------- #
# ---- CONSTANTS: DEFINE CONSTANTS USED IN THE GAME INCLUDING NUMBER OF PLAYERS, ROUNDS AND TRIAL SEQUENCE------ #
# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #

# Generate a trial sequence for the experiment based on the number of rounds and reversal rounds
# The sequence is generated randomly with reversal rounds every 8-12 rounds, but remains the same for all groups

def generate_trial_sequence():
    # Using a fixed random seed ensures the same sequence is generated each time the experiment runs
    # This is important for reproducibility and consistency across different groups
    random.seed(49)  # You can change this number, but keep it constant

    sequence = []
    # Randomly select which image will start as the high-probability option
    current_image = random.choice(['option1A.bmp', 'option1B.bmp'])
    reversal_rounds = []
    
    # Create a list of rounds where reversals will occur
    # Reversals happen every 8-12 rounds (randomly determined)
    current_round = random.randint(8, 12)
    while current_round <= NUM_ROUNDS:
        reversal_rounds.append(current_round)
        current_round += random.randint(8, 12)
    
    # Generate the full sequence of trials
    # At each reversal round, the high-probability image switches
    for round_number in range(1, NUM_ROUNDS + 1):
        if round_number in reversal_rounds:
            current_image = 'option1B.bmp' if current_image == 'option1A.bmp' else 'option1A.bmp'
        sequence.append((round_number, current_image))

    # Save sequence to CSV
    file_path = os.path.join(os.getcwd(), 'reversal_sequence.csv')
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['round', 'seventy_percent_image', 'is_reversal'])
        for round_num, image in sequence:
            writer.writerows([(round_num, image, round_num in reversal_rounds)])

    print(f"Reversal rounds: {reversal_rounds}")
    return sequence, reversal_rounds

# -------------------------------------------------------------------------------------------------------------------- #
# ---- REWARD SEQUENCE: GENERATE A SEQUENCE OF REWARDS FOR THE EXPERIMENT BASED ON THE NUMBER OF ROUNDS ------ #

# Define the core parameters of the experiment
NUM_ROUNDS = 60  # Total number of rounds in the experiment
REWARD_PROBABILITY_A = 0.7  # 70% chance of reward for option A when it's the high-probability option
REWARD_PROBABILITY_B = 0.3  # 30% chance of reward for option A when it's the low-probability option
DECISION_TIME = 3.0 # Time limit for making choices and bets (3 seconds)

# This function generates the actual sequence of rewards that players will receive
# It ensures a balanced distribution of rewards while maintaining the intended probabilities
def generate_reward_sequence(num_rounds, reversal_rounds):
    sequence = []
    current_high_prob_image = 'A'  # Start with image A as high probability
    high_prob_rewards = 0  # Counter for high probability rewards given
    low_prob_rewards = 0   # Counter for low probability rewards given
    target_high_rewards = 42  # Target number of high probability rewards (70% of 60 rounds)
    target_low_rewards = 18   # Target number of low probability rewards (30% of 60 rounds)

    # Prepare CSV file headers for logging the reward sequence
    csv_data = [['Round', 'High Prob', 'reward_A', 'reward_B']]

    print("\nGenerated Reward Sequence:")
    print("Round | High Prob | reward_A | reward_B")
    print("------|-----------|----------|----------")

    # Helper function to prevent too many consecutive high probability rewards
    def can_add_high_prob():
        if len(sequence) < 3:
            return True
        return not all(s[0] if current_high_prob_image == 'A' else s[1] for s in sequence[-3:])

    # Helper function to prevent too many consecutive low probability rewards
    def can_add_low_prob():
        if len(sequence) < 3:
            return True
        return not all(s[1] if current_high_prob_image == 'A' else s[0] for s in sequence[-3:])

    # Generate rewards for each round
    for round_num in range(1, num_rounds + 1):
        # Switch the high probability image at reversal rounds
        if round_num in reversal_rounds:
            current_high_prob_image = 'B' if current_high_prob_image == 'A' else 'A'
            print("-------|-----------|----------|----------")
            csv_data.append(['-------|-----------|----------|----------'])

        # Calculate how many more rewards are needed of each type
        remaining_rounds = num_rounds - round_num + 1
        min_high_needed = target_high_rewards - high_prob_rewards
        min_low_needed = target_low_rewards - low_prob_rewards

        # Logic to ensure we meet our target numbers while maintaining randomness
        if min_high_needed > remaining_rounds * 0.7:
            choice = 'high'
        elif min_low_needed > remaining_rounds * 0.3:
            choice = 'low'
        elif not can_add_high_prob():
            choice = 'low'
        elif not can_add_low_prob():
            choice = 'high'
        else:
            choice = random.choices(['high', 'low'], weights=[0.7, 0.3])[0]

        # Assign rewards based on the choice
        if choice == 'high' and can_add_high_prob():
            reward_A, reward_B = (1, 0) if current_high_prob_image == 'A' else (0, 1)
            high_prob_rewards += 1
        else:
            reward_A, reward_B = (0, 1) if current_high_prob_image == 'A' else (1, 0)
            low_prob_rewards += 1

        sequence.append((reward_A, reward_B))
        print(f"{round_num:5d} | {current_high_prob_image:9s} | {reward_A:8d} | {reward_B:8d}")
        csv_data.append([round_num, current_high_prob_image, reward_A, reward_B])

    # Calculate and display statistics about the generated sequence
    high_prob_percentage = (high_prob_rewards / num_rounds) * 100
    low_prob_percentage = (low_prob_rewards / num_rounds) * 100
    
    print("\nReward Statistics:")
    print(f"High probability rewards: {high_prob_rewards}/{num_rounds} ({high_prob_percentage:.2f}%)")
    print(f"Low probability rewards: {low_prob_rewards}/{num_rounds} ({low_prob_percentage:.2f}%)")

    # Save the complete reward sequence to a CSV file
    with open('reward_sequence.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_data)

    print("Reward sequence saved to 'reward_sequence.csv'")

    return sequence

# Generate all sequences needed for the experiment when this module is first imported
TRIAL_SEQUENCE, REVERSAL_ROUNDS = generate_trial_sequence()
REWARD_SEQUENCE = generate_reward_sequence(60, REVERSAL_ROUNDS)

# -------------------------------------------------------------------------------------------------------------------- #
# Base Constants: Used to define constants across all pages and subsessions in the game
# This class defines the fundamental parameters and settings that will be used throughout the experiment

class C(BaseConstants):
    # URL path for accessing this task in the browser
    NAME_IN_URL = 'main_task'
    
    # Number of players that form a group in the experiment
    PLAYERS_PER_GROUP = 5
    
    # Total number of rounds in the experiment (defined earlier as 60)
    NUM_ROUNDS = NUM_ROUNDS
    
    # The reward probabilities for each option
    # When an option is in its "high probability" state, it has a 70% chance of giving a reward
    # When an option is in its "low probability" state, it has a 30% chance of giving a reward
    REWARD_PROBABILITY_A = REWARD_PROBABILITY_A
    REWARD_PROBABILITY_B = REWARD_PROBABILITY_B
    
    # The image files that represent the two choice options players can select between
    IMAGES = ['option1A.bmp', 'option1B.bmp']
    
    # The avatar image used to represent players in the interface
    AVATAR_IMAGE = 'main_task/avatar_male.png'
    
    # Dictionary mapping image names to their full file paths in the static directory
    # Includes both regular images and transparent versions (with '_tr' suffix)
    IMAGE_PATHS = {
        'option1A.bmp': '_static/main_task/option1A.bmp',
        'option1B.bmp': '_static/main_task/option1B.bmp',
        'option1A_tr.bmp': '_static/main_task/option1A_tr.bmp',
        'option1B_tr.bmp': '_static/main_task/option1B_tr.bmp',
        'avatar_male.png': '_static/main_task/avatar_male.png',
    }
    
    # The pre-generated sequence of rewards that will be used throughout the experiment
    REWARD_SEQUENCE = REWARD_SEQUENCE

# -------------------------------------------------------------------------------------------------------------------- #
# This function generates a sequence determining which choice (first or second) will count for earnings in each round
# This adds an element of uncertainty as players don't know which of their two choices will determine their earnings

def generate_earnings_sequence(num_rounds):
    # Use a fixed random seed for reproducibility
    random.seed(42)  # Ensure reproducibility
    
    # Create initial sequence alternating between first and second choice earnings
    sequence = ['choice1_earnings' if i % 2 == 0 else 'choice2_earnings' for i in range(num_rounds)]
    
    # Shuffle the sequence to make it unpredictable
    random.shuffle(sequence)
    
    # Debug print statement (commented out)
    for i, earnings_type in enumerate(sequence, 1):
        pass # print(f"Round {i}: {earnings_type}") # Uncomment to print the sequence of earnings types
    
    return sequence

# Generate the earnings sequence when the module is imported
EARNINGS_SEQUENCE = generate_earnings_sequence(NUM_ROUNDS)

# -------------------------------------------------------------------------------------------------------------------- #
# ---- SUBSESSIONS: USED TO DEFINE THE ROUNDS FOR REVERSAL AND BOTS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# A subsession represents one round of the game

class Subsession(BaseSubsession):
    # This method handles grouping players as they arrive
    # It is only used when group_by_arrival_time = True
    def group_by_arrival_time_method(self, waiting_players):
        # Form groups of 5 when enough players are available
        if len(waiting_players) >= 5:
            return waiting_players[:5]
        return None

    # This method is called when creating a new session or round
    def creating_session(self):
        # Initialize trial number at start of each round
        self.trial_number = self.round_number

        # For rounds after first, maintain group structure from round 1
        # This ensures groups formed by arrival time persist across rounds
        if self.round_number > 1:
            self.group_like_round(1)

        # Initialize fields for all groups and players
        for group in self.get_groups():
            group.round_reward_set = False
            group.round_reward_A = None
            group.round_reward_B = None
            
            # Initialize fields for all players
            for player in group.get_players():
                # Initialize required fields
                images = C.IMAGES.copy()
                random.shuffle(images)
                player.left_image = images[0]
                player.right_image = images[1]
                player.chosen_image_one = None
                player.chosen_image_two = None
                player.bet1 = 0
                player.bet2 = 0
        
        # For all rounds after the first, ensure reward settings are reset
        if self.round_number > 1:
            for group in self.get_groups():
                group.round_reward_set = False
                
            # Check connection status of all players
            for player in self.get_players():
                if hasattr(player, 'last_connection_time'):
                    time_since_connection = time.time() - player.last_connection_time
                    if time_since_connection > 10:  # 10 seconds threshold
                        player.increment_disconnect_streak()

    # Returns a list of all reversal rounds up to the current round
    # This helps track when probability switches have occurred
    def get_reversal_rounds(self):
        return [round for round in REVERSAL_ROUNDS if round <= self.round_number]

    # Method to collect data from all players in a format suitable for bot testing
    # This is useful for debugging and testing the application
    def collect_bot_data(self):
        data = []
        for p in self.get_players():
            player_data = {
                'round_number': self.round_number,
                'player_id': p.id_in_group,
                'choice1': p.choice1,          # First choice made by player
                'bet1': p.bet1,               # First bet amount
                'choice2': p.choice2,          # Second choice made by player
                'bet2': p.bet2,               # Second bet amount
                'trial_reward': p.trial_reward,  # Reward received in this trial
                'choice2_earnings': p.choice2_earnings  # Earnings from second choice
            }
            data.append(player_data)
        return data

# -------------------------------------------------------------------------------------------------------------------- #
# ---- GROUP-LEVEL VARIABLES: USED TO TRACK ROUND REWARDS, REWARD PROBABILITIES AND INTERTRIAL INTERVALS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# This class defines variables and methods that affect the entire group of players simultaneously

class Group(BaseGroup):
    # Core tracking variables for the group
    current_round = models.IntegerField(initial=1)     # Sets the current round
    trial_number = models.IntegerField(initial=1)      # Track the current trial number
    my_page_load_time = models.FloatField()            # Records when the page loads for the group
    round_reward_A = models.IntegerField()             # Reward for option A in current round
    round_reward_B = models.IntegerField()             # Reward for option B in current round
    intertrial_interval = models.IntegerField(initial=0)  # Time gap between trials (3000-4000ms)
    
    # Control flags for timing and state management
    second_bet_timer_ended_executed = models.BooleanField(initial=False)  # Tracks if second betting phase has ended
    next_round_transition_time = models.FloatField()    # When to transition to next round
    
    # Probability settings for the two options
    reward_probability_A = models.FloatField(initial=0.7)  # Starting probability for option A
    reward_probability_B = models.FloatField(initial=0.3)  # Starting probability for option B
    
    # Track which image has which probability
    seventy_percent_image = models.StringField(initial='option1A.bmp')  # Image with 70% reward chance
    thirty_percent_image = models.StringField(initial='option1B.bmp')   # Image with 30% reward chance
    
    # State tracking variables
    reversal_rounds = models.StringField(initial='')    # Records when probability reversals occur
    bet_container_displayed = models.BooleanField(initial=False)  # Whether betting UI is shown
    remaining_images_displayed = models.BooleanField(initial=False)  # Whether all choices are displayed
    reversal_happened = models.BooleanField(initial=False)  # If a probability reversal occurred this round
    round_reward_set = models.BooleanField(initial=False)  # If rewards have been set for this round
    
    # Page loading coordination
    all_players_loaded = models.BooleanField(initial=False)  # If all players have loaded the page
    players_loaded_count = models.IntegerField(initial=0)    # Number of players who have loaded
    disconnected_players = models.StringField(initial="")   # Track players who have disconnected
    bot_players = models.StringField(initial="")           # Track players who have bots activated
    active_bots = models.StringField(initial="")       # Track bots that are currently active
    disconnection_streaks = models.StringField(initial="{}")  # Track disconnection streaks for all players

#### ---------------- Define the bot ------------------------ ####
# This method activates a bot for a player who has disconnected from the game 
# The bot will make choices and bets on behalf of the disconnected player(s) to ensure the game continues

    def activate_bot(self, player):
        """Activate a bot for a disconnected player"""
        if player.is_bot:
            logging.info(f"Bot already active for player {player.id_in_group}")
            return

        try:
            logging.info(f"Activating bot for player {player.id_in_group}")
            player.is_bot = True
            
            # Ensure bot has valid image fields
            if player.field_maybe_none('left_image') is None:
                player.left_image = C.IMAGES[0]
            if player.field_maybe_none('right_image') is None:
                player.right_image = C.IMAGES[1]
            
            # Initialize other necessary fields
            player.participant.vars['is_bot'] = True
            player.participant.vars['timed_out'] = True
            
            bot = PlayerBot(player)
            def run_bot():
                try:
                    logging.info(f"Bot starting round for player {player.id_in_group}")
                    for submission in bot.play_round():
                        try:
                            submission.submit()
                        except Exception as e:
                            logging.error(f"Bot submission error: {e}")
                    logging.info(f"Bot completed round for player {player.id_in_group}")
                except Exception as e:
                    logging.error(f"Bot runtime error: {e}")
                    
            threading.Thread(target=run_bot).start()
                
        except Exception as e:
            logging.error(f"Bot activation failed: {e}")
            player.is_bot = False
    
    def get_players(self):
        """Optimized method to get players with pre-fetched related data"""

        # Get the player model for the current app
        PlayerModel = self.player_set.model

        # Use the model manager to build the query
        return (PlayerModel.objects
                .filter(group=self)
                .select_related('participant')
                .prefetch_related(
                    Prefetch('in_previous_rounds')
                )
                .order_by('id_in_group'))

#### ---------------- Define the round reward ------------------------ ####
# Sets up the rewards for each option in the current round based on the pre-generated sequence

    def set_round_reward(self):
        # Only set rewards once per round
        if not self.round_reward_set:
            # Get rewards from the pre-generated sequence
            self.round_reward_A, self.round_reward_B = C.REWARD_SEQUENCE[self.round_number - 1]
            self.round_reward_set = True
            print(f"Round {self.round_number}: reward_A = {self.round_reward_A}, reward_B = {self.round_reward_B}")

    def calculate_player_rewards(self):
        # Calculate rewards for each player based on their second choice
        for p in self.get_players():
            # Skip players who haven't made their second choice yet
            if p.field_maybe_none('chosen_image_two') is None:
                continue

            # Determine reward based on which image was chosen and which has high probability
            if p.chosen_image_two == self.seventy_percent_image:
                potential_reward = self.round_reward_A if self.seventy_percent_image == 'option1A.bmp' else self.round_reward_B
            else:
                potential_reward = self.round_reward_B if self.seventy_percent_image == 'option1A.bmp' else self.round_reward_A

            p.trial_reward = potential_reward

#### ---------------- Define payoffs ------------------------ ####
# Calculates earnings for each player based on their choices, bets, and the rewards

    def set_payoffs(self):
        # Ensure rewards are set and calculated for all players
        self.set_round_reward()
        self.calculate_player_rewards()

        print(f"\n--- Round {self.round_number} Results ---")

        for p in self.get_players():
            # Calculate earnings for second choice: bet amount * 20 * reward (1 or 0)
            # If reward is 0, player loses their bet amount * 20
            p.choice2_earnings = p.bet2 * 20 * p.trial_reward if p.trial_reward == 1 else -1 * p.bet2 * 20
            
            # Calculate earnings for first choice similarly
            choice1_reward = 0
            chosen_image_one = p.field_maybe_none('chosen_image_one')
            
            # Determine reward based on which image was chosen and which has high probability
            if chosen_image_one == 'option1A.bmp':
                choice1_reward = self.round_reward_A
            elif chosen_image_one == 'option1B.bmp':
                choice1_reward = self.round_reward_B
            
            p.choice1_earnings = p.bet1 * 20 * choice1_reward if choice1_reward == 1 else -1 * p.bet1 * 20

        print("-----------------------------\n")

#### --------------- Define the intertrial interval ------------------------ ####
# Creates a random pause between trials to prevent rhythmic responding

    def generate_intertrial_interval(self):
        # Generate random interval between 3 and 4 seconds
        self.intertrial_interval = random.randint(3000, 4000)
        print(f"Intertrial interval of {self.intertrial_interval}ms generated")

#### ----------- Define and record the reversal learning rounds ------------------- ####
# Manages the switching of reward probabilities between the two options

    def reversal_learning(self):
        """Handle reversal learning trials where probability mappings between images change"""
        
        try:
            # Check if this is a reversal round
            is_reversal = self.round_number in REVERSAL_ROUNDS
            
            # Find current round data
            current_round_data = next((item for item in TRIAL_SEQUENCE if item[0] == self.round_number), None)
            print(f"Current round data: {current_round_data}")
            
            # If data is found, update the probabilities and images for the current round based on the sequence
            if current_round_data:
                self.reversal_happened = is_reversal
                new_seventy_percent_image = current_round_data[1]
                new_thirty_percent_image = 'option1B.bmp' if new_seventy_percent_image == 'option1A.bmp' else 'option1A.bmp'
                
                # Update values
                self.seventy_percent_image = new_seventy_percent_image
                self.thirty_percent_image = new_thirty_percent_image
                
                if self.seventy_percent_image == 'option1A.bmp':
                    self.reward_probability_A = 0.7
                    self.reward_probability_B = 0.3
                else:
                    self.reward_probability_A = 0.3
                    self.reward_probability_B = 0.7
                
        except Exception as e:
            print(f"ERROR in reversal_learning: {e}")
            import traceback
            traceback.print_exc()

#### ------------- Define the reset fields method ------------------- ####
# Resets all group-level variables to their initial states at the start of each round

    def reset_fields(self):
        """Reset only control flags and temporary variables, not probability settings"""

        # Reset control flags and temporary variables only
        self.my_page_load_time = None
        self.round_reward_A = 0
        self.round_reward_B = 0
        self.intertrial_interval = 0
        self.second_bet_timer_ended_executed = False
        self.next_round_transition_time = None
        self.bet_container_displayed = False
        self.remaining_images_displayed = False
        self.round_reward_set = False

# -------------------------------------------------------------------------------------------------------------------- #
# ---- PLAYER-LEVEL VARIABLES: USED TO TRACK CHOICES, BETS, EARNINGS AND A WHOLE LOT ELSE ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# The Player class is used to define the variables that are stored at the player level
# The variables include choices, bets, rewards, and timings for each player

class Player(BasePlayer):
    # Choice and bet tracking variables
    choice1 = models.StringField(initial='')              # Player's first choice ('left' or 'right')
    choice2 = models.StringField(initial='')              # Player's second choice
    computer_choice1 = models.StringField(initial='')     # Computer's choice if player doesn't respond in time (first)
    computer_choice2 = models.StringField(initial='')     # Computer's choice if player doesn't respond in time (second)
    bet1 = models.IntegerField(initial=0)                # Amount bet on first choice (1-3)
    bet2 = models.IntegerField(initial=0)                # Amount bet on second choice (1-3)
    
    # Image tracking
    left_image = models.StringField()                    # Which image is shown on left side
    right_image = models.StringField()                   # Which image is shown on right side
    trial_reward = models.IntegerField(initial=0)        # Reward received in current trial
    
    # Detailed choice tracking
    chosen_image_one = models.StringField(initial=None)              # Actual image chosen in first choice
    chosen_image_one_binary = models.IntegerField(initial=1)      # First choice coded as 1 or 2
    chosen_image_two = models.StringField(initial=None)  # Actual image chosen in second choice
    chosen_image_two_binary = models.IntegerField(initial=1)      # Second choice coded as 1 or 2
    
    # Social influence tracking
    choice1_with = models.IntegerField(initial=0)        # Number of others who made same first choice
    choice1_against = models.IntegerField(initial=0)     # Number of others who made different first choice
    choice2_with = models.IntegerField(initial=0)        # Number of others who made same second choice
    choice2_against = models.IntegerField(initial=0)     # Number of others who made different second choice
    
    # Computer choice tracking
    chosen_image_computer = models.StringField(initial='')     # Image chosen by computer for first choice
    chosen_image_computer_two = models.StringField(initial='') # Image chosen by computer for second choice
    
    # Performance metrics
    choice1_accuracy = models.BooleanField()             # Whether first choice was optimal
    choice2_accuracy = models.BooleanField()             # Whether second choice was optimal
    switch_vs_stay = models.IntegerField()               # Whether player switched (1) or stayed (0) between choices
    
    # Timing variables
    my_page_load_time = models.FloatField()             # When page loaded for this player
    individual_page_load_time = models.FloatField()      # Individual timing for page load
    initial_choice_time = models.FloatField()            # Time taken for first choice
    initial_bet_time = models.FloatField()               # Time taken for first bet
    second_choice_time = models.FloatField()             # Time taken for second choice
    second_bet_time = models.FloatField()                # Time taken for second bet
    
    # Earnings tracking
    choice1_earnings = models.IntegerField(initial=0)    # Points earned from first choice
    choice2_earnings = models.IntegerField(initial=0)    # Points earned from second choice
    choice1_sum_earnings = models.IntegerField(initial=0) # Cumulative earnings from first choices
    choice2_sum_earnings = models.IntegerField(initial=0) # Cumulative earnings from second choices
    bonus_payment_score = models.IntegerField(initial=0) # Total bonus points earned
    
    # Final payment calculations
    base_payoff = models.CurrencyField(initial=6)       # Base payment amount (£6)
    bonus_payoff = models.CurrencyField(initial=0)      # Additional bonus earned
    total_payoff = models.CurrencyField(initial=0)      # Total payment (base + bonus)
    
    # Outcome tracking
    loss_or_gain = models.IntegerField()                # Whether player gained (1) or lost (-1) points
    
    # Computer intervention flags
    computer_choice_one = models.BooleanField(initial=True)   # If computer made first choice
    computer_bet_one = models.BooleanField(initial=False)     # If computer made first bet
    computer_choice_two = models.BooleanField(initial=True)   # If computer made second choice
    computer_bet_two = models.BooleanField(initial=False)     # If computer made second bet
    
    # Other players' choices tracking
    # Track choices of all other players (1-4) for both first and second choices
    player_1_choice_one = models.IntegerField()
    player_2_choice_one = models.IntegerField()
    player_3_choice_one = models.IntegerField()
    player_4_choice_one = models.IntegerField()
    player_1_choice_two = models.IntegerField()
    player_2_choice_two = models.IntegerField()
    player_3_choice_two = models.IntegerField()
    player_4_choice_two = models.IntegerField()
    
    # Track accuracy of other players' choices
    player1_choice1_accuracy = models.BooleanField()
    player2_choice1_accuracy = models.BooleanField()
    player3_choice1_accuracy = models.BooleanField()
    player4_choice1_accuracy = models.BooleanField()
    player1_choice2_accuracy = models.BooleanField()
    player2_choice2_accuracy = models.BooleanField()
    player3_choice2_accuracy = models.BooleanField()
    player4_choice2_accuracy = models.BooleanField()
    
    # Track whether other players gained or lost points
    loss_or_gain_player1 = models.IntegerField()
    loss_or_gain_player2 = models.IntegerField()
    loss_or_gain_player3 = models.IntegerField()
    loss_or_gain_player4 = models.IntegerField()
    
    # Track if second choice was made manually
    manual_second_choice = models.BooleanField(initial=False)

    # Connection tracking fields
    disconnection_streak = models.IntegerField(initial=0)
    is_bot = models.BooleanField(initial=False)
    last_connection_time = models.FloatField(initial=0)

    last_check_time = models.FloatField(initial=0)
    consecutive_missed_checks = models.IntegerField(initial=0)

    def get_others_in_group(self):
        """Optimized method to get other players in group"""
        return super().get_others_in_group().select_related('participant')
    
    def in_previous_rounds(self):
        """Optimized method to get player's previous rounds"""
        return super().in_previous_rounds().select_related('group', 'participant')

    def in_round(self, round_number):
        """Optimized method to get player in specific round"""
        return super().in_round(round_number).select_related('group', 'participant')
    
    def log_queries(self):
        """Debug function to log number of queries"""
        return len(connection.queries)

    def check_connection(self, current_time, time_since_activity):
        # Only check every 10 seconds
        if current_time - self.last_check_time < 10:
            return False
            
        self.last_check_time = current_time
        
        # If inactive for more than 15 seconds
        if time_since_activity > 15:
            self.consecutive_missed_checks += 1
            if self.consecutive_missed_checks >= 3:
                self.increment_disconnect_streak()
                return True
        else:
            # Reset counter if activity detected
            if self.consecutive_missed_checks > 0:
                self.consecutive_missed_checks = 0
                self.reset_disconnect_streak()
                return True
                    
        return False

    # Increment the disconnection streak for a player who has been inactive for too long (10 seconds)
    # This is used to activate a bot for players who have disconnected from the game but is sensitive to page reloads
    def increment_disconnect_streak(self):
        current_time = time.time()
        last_connect_time = self.participant.vars.get('last_connect_time', 0)
        last_activity_time = self.participant.vars.get('last_activity_time', current_time)
        time_since_connect = current_time - last_connect_time
        time_since_activity = current_time - last_activity_time
        
        # Only count as disconnection if:
        # 1. Been over 10 seconds since last connection AND
        # 2. Been over 15 seconds since last activity
        if time_since_connect > 10 and time_since_activity > 15:
            current_streak = self.field_maybe_none('disconnection_streak') or 0
            self.disconnection_streak = current_streak + 1
            self.participant.vars['disconnection_streak'] = self.disconnection_streak
            
            # Only activate bot after 5 consecutive long disconnections
            if self.disconnection_streak >= 5 and not self.is_bot:
                logging.info(f"Activating bot for player {self.id_in_group} due to extended inactivity "
                            f"(streak: {self.disconnection_streak})")
                self.group.activate_bot(self)

    # Method to record when a player reconnects to the game after a disconnection
    # This is used to reset the disconnection streak and track reconnection times for page reloads
    def reset_disconnect_streak(self):
        current_time = time.time()
        last_disconnect = self.participant.vars.get('last_disconnect_time', 0)
        time_since_disconnect = current_time - last_disconnect
        
        # Only reset if connected and active for at least 20 seconds
        if time_since_disconnect >= 20:
            old_streak = self.field_maybe_none('disconnection_streak') or 0
            self.disconnection_streak = 0
            self.participant.vars['disconnection_streak'] = 0
            self.participant.vars['last_connect_time'] = current_time
            self.participant.vars['last_activity_time'] = current_time

    # Method to record when a player disconnects from the game
    def record_activity(self):
        """Record that the player is actively participating"""
        self.participant.vars['last_activity_time'] = time.time()
    
    # Field access method that safely handles null fields to prevent errors
    def field_maybe_none(self, field_name):
        """Safely access potentially null fields"""
        try:
            return super().field_maybe_none(field_name)
        except TypeError:
            logging.warning(f"Null field access for player {self.id_in_group}: {field_name}")
            return None

    def reset_fields(self):
        """Reset all player variables to their initial states at the start of each round"""
        pass
        
    def calculate_payoffs(self):
        """Calculate final payment with optimized queries"""
        self.base_payoff = cu(6)  # Base payoff of £6
        
        # Get previous rounds data efficiently in one query
        if self.round_number > 1:
            previous_rounds = self.in_previous_rounds()
            cumulative_score = sum(p.bonus_payment_score for p in previous_rounds)
            self.bonus_payment_score = cumulative_score + self.choice2_earnings
        else:
            self.bonus_payment_score = self.choice2_earnings
        
        if self.bonus_payment_score <= 0:
            self.bonus_payoff = cu(0)
        else:
            self.bonus_payoff = cu(round(self.bonus_payment_score / 750, 2))
        
        self.total_payoff = self.base_payoff + self.bonus_payoff

    def calculate_choice_comparisons(self):
        """Calculate how many others made same choices with optimized queries"""
        other_players = self.get_others_in_group()
        
        my_choice_one = self.field_maybe_none('chosen_image_one')
        my_choice_two = self.field_maybe_none('chosen_image_two')
        
        if my_choice_one is not None:
            self.choice1_with = sum(1 for p in other_players 
                                if p.field_maybe_none('chosen_image_one') == my_choice_one)
            self.choice1_against = len(other_players) - self.choice1_with
        else:
            self.choice1_with = 0
            self.choice1_against = 0
        
        if my_choice_two is not None:
            self.choice2_with = sum(1 for p in other_players 
                                if p.field_maybe_none('chosen_image_two') == my_choice_two)
            self.choice2_against = len(other_players) - self.choice2_with
        else:
            self.choice2_with = 0
            self.choice2_against = 0

    def calculate_choice1_earnings(self):
        """Calculate earnings from first choice with optimized queries"""
        if self.chosen_image_one == 'option1A.bmp':
            choice1_reward = self.group.field_maybe_none('round_reward_A') or 0
        elif self.chosen_image_one == 'option1B.bmp':
            choice1_reward = self.group.field_maybe_none('round_reward_B') or 0
        else:
            return

        self.choice1_earnings = self.bet1 * 20 * choice1_reward if choice1_reward == 1 else -1 * self.bet1 * 20

# -------------------------------------------------------------------------------------------------------------------- #
# ---- WAIT AND TRANSITION PAGES: USED TO FORM GROUPS BY ARRIVAL TIME ON THE APP ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class WaitPage2(WaitPage):
    template_name = 'main_task/WaitPage2.html'  # Move template to main_task templates
    group_by_arrival_time = True

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        return {
            'title_text': 'Waiting for Other Players',
        }
  
    @staticmethod              
    def js_vars(player):
        return dict(
            waitpagelink=player.subsession.session.config['waitpagelink']
        )

class TransitionToMainTask(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    def vars_for_template(self):
        return {
            'transition_time': 15,
        }
    
# -------------------------------------------------------------------------------------------------------------------- #
# ---- MYPAGE: WHERE PLAYERS MAKE THEIR FIRST CHOICE, FIRST BET AND PREFERENCE CHOICES ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class MyPage(Page):
    # Tell oTree which model to use and which fields to expect from the form
    form_model = 'player'
    form_fields = ['choice1', 'bet1', 'choice2', 'bet2']

    # js_vars method is used to pass variables to the JavaScript template
    @staticmethod
    def js_vars(player: Player):
        # Pass the start time to JavaScript for timing calculations
        return dict(
            page_start_time=int(time.time() * 1000),  # Current time in milliseconds
            connection_check_interval=10000  # 10 seconds
        )
    
    # Define the timeout for this page
    @staticmethod
    def get_timeout_seconds(player: Player):
        # Set page timeout to 100 seconds (10000 milliseconds)
        return 10000

    # before_next_page method is called before moving to the next page 
    # It's used to process the player's choices and bets
    @staticmethod
    def before_next_page(player: Player, timeout_happened):

        # Add at the start of the method:
        current_streak = player.field_maybe_none('disconnection_streak') or 0
        if current_streak >= 5 and not player.is_bot:
            logging.info(f"before_next_page: Activating bot for player {player.id_in_group} (streak: {current_streak})")
            player.group.activate_bot(player)
            player.participant.vars['timed_out'] = True

        # Check for disconnected players
        if not player.participant.vars.get('is_connected', True):
            # Record disconnection time if not already set
            if 'disconnection_time' not in player.participant.vars:
                player.participant.vars['disconnection_time'] = time.time()
            
            # If disconnected for more than 10 seconds, activate bot
            if time.time() - player.participant.vars['disconnection_time'] > 10:
                logging.info(f"Player {player.id_in_group} disconnected for over 10 seconds at end of round {player.round_number}")
                player.group.player_disconnected(player.id_in_group)

        # Handle what happens when the page times out
        if timeout_happened:
            player.participant.vars['timed_out'] = True

        # Prefetch previous round data if needed
        if player.round_number > 1:
            previous_player = player.in_round(player.round_number - 1).select_related('group')
        
        # Process both first and second choices/bets using the same logic
        for choice_field, computer_choice_field, bet_field, image_field in [
            ('choice1', 'computer_choice1', 'bet1', 'chosen_image_one'),
            ('choice2', 'computer_choice2', 'bet2', 'chosen_image_two')
        ]:
            manual_choice = player.field_maybe_none(choice_field)
            computer_choice = player.field_maybe_none(computer_choice_field)

            # Decision tree for handling choices
            if manual_choice is not None and (computer_choice is None or computer_choice not in ['left', 'right']):
                pass  # Keep the manual choice
            elif computer_choice in ['left', 'right']:
                setattr(player, choice_field, None)
                setattr(player, computer_choice_field, computer_choice)
            elif manual_choice is None and computer_choice is None:
                setattr(player, choice_field, None)
                setattr(player, computer_choice_field, None)

            # Determine final choice and set chosen image
            final_choice = getattr(player, computer_choice_field) or getattr(player, choice_field)
            if final_choice in ['left', 'right']:
                chosen_image = player.left_image if final_choice == 'left' else player.right_image
                setattr(player, image_field, chosen_image)
                player.participant.vars[image_field] = chosen_image
            else:
                setattr(player, image_field, None)
                player.participant.vars[image_field] = None

            # Set default bet
            bet_value = player.field_maybe_none(bet_field)
            if bet_value is None:
                setattr(player, bet_field, 1)

        # Calculate earnings with prefetched data
        player.calculate_choice1_earnings()
        player.choice2_earnings = player.bet2 * 20 * player.trial_reward if player.trial_reward == 1 else -1 * player.bet2 * 20

        # Get earnings type and calculate current round earnings
        earnings_type = EARNINGS_SEQUENCE[player.round_number - 1]
        current_round_earnings = player.choice1_earnings if earnings_type == 'choice1_earnings' else player.choice2_earnings

        # Update cumulative scores efficiently
        if player.round_number == 1:
            player.bonus_payment_score = current_round_earnings
            player.choice1_sum_earnings = player.choice1_earnings
            player.choice2_sum_earnings = player.choice2_earnings
        else:
            # Use prefetched previous round data
            player.bonus_payment_score = previous_player.bonus_payment_score + current_round_earnings
            player.choice1_sum_earnings = previous_player.choice1_sum_earnings + player.choice1_earnings
            player.choice2_sum_earnings = previous_player.choice2_sum_earnings + player.choice2_earnings

        # Calculate metrics using prefetched data
        player.calculate_choice_comparisons()
        player.choice1_accuracy = player.chosen_image_one == player.group.seventy_percent_image
        player.choice2_accuracy = player.chosen_image_two == player.group.seventy_percent_image
        player.switch_vs_stay = 1 if player.chosen_image_one != player.chosen_image_two else 0

    # app_after_this_page method is used to redirect players who have timed out to a different page
    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        # If player timed out, redirect them to the timeout page
        if player.participant.vars.get('timed_out', False):
            return 'submission'

    # vars_for_template method is used to pass variables to the template
    # This is used to display information to the player in the interface
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        
        # Use optimized query to get players
        players = group.get_players()

        if player.id_in_group == 1:
            group.reversal_learning()
            group.reset_fields()
            for p in players:
                p.reset_fields()

        for p in players:
            current_streak = p.field_maybe_none('disconnection_streak')
            if current_streak is not None and current_streak > 0:
                logging.info(f"Start of round {group.round_number}: Player {p.id_in_group} has streak of {current_streak}/5")
                if current_streak >= 5 and not p.is_bot:
                    p.increment_disconnect_streak()
        
        player.last_connection_time = time.time()

        try:
            images = C.IMAGES.copy()
            random.shuffle(images)
            left_image = images[0]
            right_image = images[1]

            player.left_image = left_image
            player.right_image = right_image

        except Exception as e:
            logging.error(f"Failed to set images for player {player.id_in_group}: {e}")
            left_image = 'option1A.bmp'
            right_image = 'option1B.bmp'
            player.left_image = left_image 
            player.right_image = right_image

        # Get other players efficiently
        other_players = player.get_others_in_group()

        return {
            'left_image': f'main_task/{left_image}',
            'right_image': f'main_task/{right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': [p.id_in_group for p in other_players],
            'chosen_images': {p.id_in_group: f"main_task/{p.field_maybe_none('chosen_image_computer') or p.field_maybe_none('chosen_image_one') or 'default_image.png'}" for p in players},
            'previous_choice': player.participant.vars.get('chosen_image_one'),
            'previous_bet': player.participant.vars.get('bet1'),
            'round_number': player.round_number,
        }

# -------------------------------------------------------------------------------------------------------------------- #
# -------- The live_method: Used to handle real-time data from the players and progress them through the task--------- #
# -------------------------------------------------------------------------------------------------------------------- #

# ---- Handles real-time interactions for the first page of each round
# ---- Manages page load times, choice phases, bet phases, and preference choices
# ---- Coordinates timers and computer-assigned choices/bets when players don't respond
# ---- Calculates and updates player comparisons and accuracies
# ---- Controls the flow of the game, including display of choices and transition to next stages
# ---- Processes and responds to various events triggered by player actions or timeouts

# --- If players do not respond within the time limit, the computer randomly selects a choice or bet for them

    @staticmethod
    def live_method(player, data):
        if player.field_maybe_none('is_bot'):
            # Ensure bot has valid image fields
            if player.field_maybe_none('left_image') is None:
                player.left_image = C.IMAGES[0]
            if player.field_maybe_none('right_image') is None:
                player.right_image = C.IMAGES[1]
        # print(f"Received data: {data}") # Uncomment to print received data

        # Initialize response dictionary and get references to group and all players
        group = player.group
        players = group.get_players()
        response = {}

        # Handle activity recording
        if 'record_activity' in data:
            try:
                player.record_activity()
            except Exception as e:
                logging.error(f"Error recording activity for player {player.id_in_group}: {e}")
            return

        # Handle connection checks
        if 'check_connection' in data:
            try:
                current_time = time.time()
                time_since_activity = data.get('time_since_activity', 0) / 1000  # Convert ms to seconds
                
                # Only process if connection status actually changed
                if player.check_connection(current_time, time_since_activity):
                    logging.info(f"Player {player.id_in_group} connection status changed")
                    
                    # Only activate bot if genuinely disconnected
                    if (player.field_maybe_none('disconnection_streak') >= 5 and 
                        not player.is_bot):
                        player.group.activate_bot(player)
                        
                return  # Exit early if just a routine check
                
            except Exception as e:
                logging.error(f"Error in connection check: {e}")
                return

        # Handle disconnection notifications
        if 'connection_lost' in data:
            try:
                current_time = time.time()
                last_connect = player.participant.vars.get('last_connect_time', current_time)
                time_since_connect = current_time - last_connect
                duration = data.get('duration', 0) / 1000  # Convert ms to seconds
                consecutive_failures = data.get('consecutive_failures', 0)
                
                # Record disconnect time
                player.participant.vars['last_disconnect_time'] = current_time
                
                # Only process as disconnection if:
                # 1. Been connected long enough (>10s)
                # 2. Multiple consecutive failures
                # 3. Significant duration of inactivity
                if (time_since_connect > 10 and 
                    consecutive_failures >= 3 and 
                    duration > 15):
                    logging.info(f"Processing disconnect for player {player.id_in_group} "
                            f"after {time_since_connect:.1f}s connected "
                            f"(inactive: {duration:.1f}s, failures: {consecutive_failures})")
                    player.increment_disconnect_streak()
            except Exception as e:
                logging.error(f"Error processing connection loss for player {player.id_in_group}: {e}")
            return

        # Handle connection restoration
        if 'connection_restored' in data:
            logging.info(f"Connection restored for player {player.id_in_group}")
            player.reset_disconnect_streak()
            return

        # ---- PAGE LOAD PHASE ----
        # Handle initial page loading and synchronization between players

        # Check if player has loaded the page
        if 'my_page_load_time' in data:
            # Convert and record load times for individual player
            player.my_page_load_time = round(data['my_page_load_time'] / 1000, 2)
            player.individual_page_load_time = round(data['individual_page_load_time'] / 1000, 2)
            
            # Track number of players who have loaded the page
            if not player.field_maybe_none('my_page_load_time'):
                group.players_loaded_count += 1
            
            # Check if all connected players have loaded
            connected_players = [p for p in players if p.field_maybe_none('last_connection_time') > 0]
            all_connected_loaded = all(
                p.field_maybe_none('my_page_load_time') is not None 
                for p in connected_players
            )
            
            # When all connected players are loaded and have page load times
            if all_connected_loaded and len(connected_players) > 0:
                # Calculate and record group page load time
                group.my_page_load_time = round(max(p.my_page_load_time for p in connected_players), 2)
                
                # Handle reversals FIRST
                group.reversal_learning()
                
                # Then set rewards
                group.set_round_reward()
                
                # Signal all players to show content and start timer
                return {p.id_in_group: dict(start_choice_phase_timer=True) for p in players}
            
            return {player.id_in_group: dict(acknowledged=True)}

        # ---- FIRST CHOICE PHASE ----
        # Handle player's first choice and timing

        if 'initial_choice_time' in data:
            # Calculate and record how long the player took to make their choice
            if data['initial_choice_time'] is not None:
                actual_choice_time = round((data['initial_choice_time'] - player.individual_page_load_time) / 1000, 2)
                player.initial_choice_time = min(actual_choice_time, DECISION_TIME)  # Cap at 3 seconds
            else:
                player.initial_choice_time = DECISION_TIME

            # Record player's manual choice if made
            if 'choice' in data and not player.field_maybe_none('chosen_image_one'):
                player.choice1 = data['choice']
                player.chosen_image_one = player.left_image if data['choice'] == 'left' else player.right_image
                player.participant.vars['chosen_image_one'] = player.chosen_image_one
                player.computer_choice_one = False  # Mark as manual choice

        # ---- CHOICE TIMER END PHASE ----
        # Handle what happens when the choice timer expires

        if 'choice_phase_timer_ended' in data:
            choices_to_process = False
            
            try:
                # Process choices for all players
                for p in players:
                    try:
                        # If player hasn't made a choice, computer makes one
                        if p.field_maybe_none('choice1') is None or p.choice1 == '':
                            choices_to_process = True
                            
                            # Ensure valid image fields exist
                            left_img = p.field_maybe_none('left_image')
                            right_img = p.field_maybe_none('right_image')
                            
                            if left_img is None:
                                left_img = C.IMAGES[0]
                                p.left_image = left_img
                            if right_img is None:
                                right_img = C.IMAGES[1]
                                p.right_image = right_img
                                
                            random_choice = random.choice(['left', 'right'])
                            
                            # Record computer's choice
                            p.choice1 = random_choice
                            p.computer_choice1 = random_choice
                            p.chosen_image_one = left_img if random_choice == 'left' else right_img
                            p.participant.vars['chosen_image_one'] = p.chosen_image_one
                            p.initial_choice_time = DECISION_TIME
                            
                            # Handle binary coding and image selection
                            try:
                                p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 2
                                p.computer_choice_one = True
                                
                                # Use transparent version of image for computer choices
                                if p.chosen_image_one == 'option1A.bmp':
                                    p.chosen_image_computer = 'option1A_tr.bmp'
                                elif p.chosen_image_one == 'option1B.bmp':
                                    p.chosen_image_computer = 'option1B_tr.bmp'
                                    
                                # Check accuracy against group's high-probability image
                                if group.field_maybe_none('seventy_percent_image'):
                                    p.choice1_accuracy = p.chosen_image_one == group.seventy_percent_image
                                else:
                                    logging.error(f"seventy_percent_image not set for group in round {group.round_number}")
                                    p.choice1_accuracy = False
                                    
                            except Exception as e:
                                logging.error(f"Error processing computer choice details for player {p.id_in_group}: {e}")
                                # Set fallback values
                                p.chosen_image_one_binary = 1
                                p.computer_choice_one = True
                                p.chosen_image_computer = 'option1A_tr.bmp'
                                p.choice1_accuracy = False
                                
                        else:
                            # Record binary coding and accuracy for manual choices
                            try:
                                p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 2
                                if group.field_maybe_none('seventy_percent_image'):
                                    p.choice1_accuracy = p.chosen_image_one == group.seventy_percent_image
                                else:
                                    p.choice1_accuracy = False
                            except Exception as e:
                                logging.error(f"Error processing manual choice details for player {p.id_in_group}: {e}")
                                p.chosen_image_one_binary = 1
                                p.choice1_accuracy = False
                                
                    except Exception as e:
                        logging.error(f"Error processing choice for player {p.id_in_group}: {e}")
                        # Set safe fallback values
                        p.choice1 = 'left'
                        p.computer_choice1 = 'left'
                        p.chosen_image_one = C.IMAGES[0]
                        p.chosen_image_one_binary = 1
                        p.computer_choice_one = True
                        p.choice1_accuracy = False

                # Record information about other players' choices
                for p in players:
                    try:
                        other_players = p.get_others_in_group()
                        
                        # Initialize default values
                        choice_defaults = [1] * 4  # Default binary choices
                        accuracy_defaults = [False] * 4  # Default accuracy values
                        
                        # Try to get actual values, fall back to defaults if needed
                        for i, other_p in enumerate(other_players):
                            try:
                                # Store choice information
                                choice_defaults[i] = other_p.field_maybe_none('chosen_image_one_binary') or 1

                                # Store choice accuracy information
                                accuracy_defaults[i] = other_p.field_maybe_none('choice1_accuracy') or False

                            except Exception as e:
                                logging.error(f"Error getting other player {i+1} data for player {p.id_in_group}: {e}")
                        
                        # Assign values with fallbacks
                        p.player_1_choice_one = choice_defaults[0]
                        p.player_2_choice_one = choice_defaults[1]
                        p.player_3_choice_one = choice_defaults[2]
                        p.player_4_choice_one = choice_defaults[3]
                        
                        # Assign accuracy values
                        p.player1_choice1_accuracy = accuracy_defaults[0]
                        p.player2_choice1_accuracy = accuracy_defaults[1]
                        p.player3_choice1_accuracy = accuracy_defaults[2]
                        p.player4_choice1_accuracy = accuracy_defaults[3]
                        
                    except Exception as e:
                        logging.error(f"Error recording other players' info for player {p.id_in_group}: {e}")
                        # Set safe fallback values for all other player fields
                        for i in range(1, 5):
                            setattr(p, f'player_{i}_choice_one', 1)
                            setattr(p, f'player_{i}_computer_choice_one', 0)  # Default to 0 for manual choice
                            setattr(p, f'player{i}_choice1_accuracy', False)

                # Move to betting phase
                return {p.id_in_group: dict(
                    show_bet_container=True, 
                    start_bet_timer=True, 
                    highlight_selected_choice=p.field_maybe_none('choice1') or 'left'
                ) for p in players}
                
            except Exception as e:
                logging.error(f"Critical error in choice phase timer end: {e}")
                # Provide safe fallback response to keep game running
                return {p.id_in_group: dict(
                    show_bet_container=True,
                    start_bet_timer=True,
                    highlight_selected_choice='left'
                ) for p in players}

        # ---- FIRST BET PHASE ----
        # Handle display of betting interface

        if 'show_bet_container' in data and data['show_bet_container']:
            for p in players:
                p.calculate_choice_comparisons()

            player.participant.vars['bet_timer_started'] = True
            player.participant.vars['bet_phase_start_time'] = time.time()
            return {player.id_in_group: dict(start_bet_timer=True)}

        # Process manual bets
        if 'bet' in data:
            if not player.computer_bet_one:
                player.bet1 = int(data['bet'])
                player.participant.vars['bet1'] = player.bet1
                player.initial_bet_time = round(data['initial_bet_time'] / 1000, 2)
                player.computer_bet_one = False

        # Handle bet timer expiration
        if 'bet_timer_ended' in data:
            response = {}
            for p in players:
                # Assign computer bets if needed
                if not p.field_maybe_none('bet1') and not p.computer_bet_one:
                    random_bet = random.randint(1, 3)
                    p.bet1 = random_bet
                    p.participant.vars['bet1'] = p.bet1
                    p.initial_bet_time = DECISION_TIME
                    p.computer_bet_one = True
                    response[p.id_in_group] = dict(highlight_computer_bet=p.bet1)

            # Display all players' choices if not already shown
            if not group.remaining_images_displayed:
                group.remaining_images_displayed = True
                display_response = MyPage.display_remaining_images(player, players)
                for p in players:
                    p.participant.vars['display_phase_end_time'] = time.time() + 4
                for p_id, p_response in display_response.items():
                    p_response['start_display_timer'] = True
                    if p_id in response:
                        p_response.update(response[p_id])
                return display_response

            return response

        # ---- SECOND CHOICE PHASE ----
        # Handle manual second choices

        if 'second_choice' in data and data.get('manual_second_choice', False):
            # Record player's second choice (existing code)
            player.choice2 = data['second_choice']
            player.chosen_image_two = (player.left_image 
                if data['second_choice'] == 'left' 
                else player.right_image)
            player.participant.vars['chosen_image_two'] = player.chosen_image_two
            player.computer_choice_two = False
            player.manual_second_choice = True
            
            # Record timing (existing code)
            if data['second_choice_time'] is not None:
                actual_choice_time = round(data['second_choice_time'] / 1000, 2)
                player.second_choice_time = min(actual_choice_time, DECISION_TIME)
            else:
                player.second_choice_time = DECISION_TIME
            
            # Calculate metrics for this player
            player.chosen_image_two_binary = 1 if player.chosen_image_two == 'option1A.bmp' else 2
            player.choice2_accuracy = player.chosen_image_two == player.group.seventy_percent_image
            player.switch_vs_stay = (1 
                if player.field_maybe_none('chosen_image_one') != player.chosen_image_two 
                else 0)
            
            # Clear computer choice fields
            player.chosen_image_computer_two = ''
            player.computer_choice2 = ''
            
            # NEW CODE: Check if all players have made their second choices
            group = player.group
            all_choices_made = all(p.field_maybe_none('chosen_image_two') is not None for p in group.get_players())
            
            if all_choices_made:
                # Calculate metrics for all players
                for p in group.get_players():
                    other_players = p.get_others_in_group()
                    
                    # Record other players' choices
                    for i, other_p in enumerate(other_players):
                        # Binary choice (1 for option1A, 2 for option1B)
                        setattr(p, f'player_{i+1}_choice_two', 
                            1 if other_p.chosen_image_two == 'option1A.bmp' else 2)
                        
                        # Computer choice flag (0 for manual, 1 for computer)
                        setattr(p, f'player_{i+1}_computer_choice_two',
                            1 if other_p.computer_choice_two else 0)
                        
                        # Choice accuracy
                        setattr(p, f'player{i+1}_choice2_accuracy',
                            other_p.chosen_image_two == group.seventy_percent_image)
            
            return {
                player.id_in_group: dict(
                    highlight_selected_second_choice=player.choice2
                )
            }

        # Handle second choice timer expiration
        if 'second_choice_timer_ended' in data:
            # Process computer choices for players who didn't respond
            for p in players:
                if not p.field_maybe_none('choice2'):

                    # Set time to 3 seconds if a manual choice was not made
                    p.second_choice_time = DECISION_TIME

                    p.computer_choice2 = random.choice(['left', 'right'])
                    p.choice2 = p.computer_choice2
                    p.chosen_image_two = p.left_image if p.computer_choice2 == 'left' else p.right_image
                    
                    # Use transparent images for computer choices
                    if p.chosen_image_two == 'option1A.bmp':
                        p.chosen_image_computer_two = 'option1A_tr.bmp'
                    else:
                        p.chosen_image_computer_two = 'option1B_tr.bmp'
                
                # Calculate metrics for all choices
                if p.field_maybe_none('chosen_image_two') is not None:
                    p.chosen_image_two_binary = 1 if p.chosen_image_two == 'option1A.bmp' else 2
                    p.choice2_accuracy = p.chosen_image_two == p.group.seventy_percent_image
                    p.switch_vs_stay = 1 if p.field_maybe_none('chosen_image_one') != p.chosen_image_two else 0
                else:
                    print(f"Warning: chosen_image_two is None for player {p.id_in_group}")

            # Record information about other players' second choices
            for p in players:

                # Initialize default values
                other_players = p.get_others_in_group()
                p.player_1_choice_two = other_players[0].chosen_image_two_binary
                p.player_2_choice_two = other_players[1].chosen_image_two_binary
                p.player_3_choice_two = other_players[2].chosen_image_two_binary
                p.player_4_choice_two = other_players[3].chosen_image_two_binary

                # Set accuracy values for other players
                p.player1_choice2_accuracy = other_players[0].choice2_accuracy
                p.player2_choice2_accuracy = other_players[1].choice2_accuracy
                p.player3_choice2_accuracy = other_players[2].choice2_accuracy
                p.player4_choice2_accuracy = other_players[3].choice2_accuracy

            # Update choice comparisons
            for p in players:
                p.calculate_choice_comparisons()

            # Move to second betting phase if not already there
            if not group.bet_container_displayed:
                group.bet_container_displayed = True
                return {p.id_in_group: dict(
                    second_choice_timer_ended=True,
                    show_bet_container=True, 
                    start_second_bet_timer=True, 
                    highlight_selected_image=p.chosen_image_two,
                    computer_second_choice=p.computer_choice2 if not p.field_maybe_none('choice2') else p.choice2
                ) for p in players}
    
        # ---- SECOND BET PHASE ----
        # Handle manual second bets

        if 'second_bet' in data:
            player.bet2 = int(data['second_bet'])
            player.bet2 = player.bet2
            player.computer_bet_two = False
            player.second_bet_time = round(data['second_bet_time'] / 1000, 2)

        # Handle second bet timer expiration and round completion
        if 'second_bet_timer_ended' in data:
            if not group.second_bet_timer_ended_executed:
                group.second_bet_timer_ended_executed = True
                response = {}

                # Update trial number
                group.trial_number = player.round_number  # track trial numbers

                # Assign computer bets if needed
                for p in players:
                    if p.bet2 == 0:
                        random_bet = random.randint(1, 3)
                        p.bet2 = random_bet
                        p.bet2 = p.bet2
                        p.computer_bet_two = True
                        p.second_bet_time = DECISION_TIME
                        response[p.id_in_group] = dict(highlight_computer_second_bet=p.bet2)

                # Calculate final results for the round
                group.set_round_reward()
                group.calculate_player_rewards()

                # Calculate earnings for all players
                for p in players:
                    p.choice2_earnings = p.bet2 * 20 * p.trial_reward if p.trial_reward == 1 else -1 * p.bet2 * 20
                    p.choice2_sum_earnings = sum([prev_player.choice2_earnings for prev_player in p.in_previous_rounds()]) + p.choice2_earnings
                    p.loss_or_gain = -1 if p.choice2_earnings < 0 else 1

                # Record gains/losses for other players
                for p in players:
                    other_players = p.get_others_in_group()
                    p.loss_or_gain_player1 = 0 if other_players[0].choice2_earnings < 0 else 1
                    p.loss_or_gain_player2 = 0 if other_players[1].choice2_earnings < 0 else 1
                    p.loss_or_gain_player3 = 0 if other_players[2].choice2_earnings < 0 else 1
                    p.loss_or_gain_player4 = 0 if other_players[3].choice2_earnings < 0 else 1

                # Generate random delay before next round
                group.generate_intertrial_interval()
                group.next_round_transition_time = time.time() * 1000 + group.intertrial_interval

                # Prepare final display information
                # Create dictionaries mapping player IDs to their chosen images and win/loss status
                chosen_images_secondchoicepage = {
                    p.id_in_group: f"main_task/{p.chosen_image_computer_two if p.computer_choice_two else p.chosen_image_two}" 
                    for p in players
                }
                win_loss_images = {p.id_in_group: f'main_task/{"win" if p.trial_reward == 1 else "loss"}.png' for p in players}

                # Prepare final response for each player
                for p in players:
                    response[p.id_in_group] = {
                        **response.get(p.id_in_group, {}),  # Preserve any existing response data
                        **dict(
                            show_results=True,              # Signal to show results screen
                            second_bet_reward=p.choice2_earnings,  # Points earned/lost
                            chosen_images=chosen_images_secondchoicepage,  # All players' final choices
                            win_loss_images=win_loss_images,      # Win/loss indicators for all
                            player_win_loss_image=win_loss_images[p.id_in_group],  # This player's result
                            intertrial_interval=group.intertrial_interval,  # Time until next round
                            round_number=player.round_number,     # Current round number
                            num_rounds=C.NUM_ROUNDS,             # Total rounds in game
                            selected_bet=p.bet2,                 # Final bet amount
                            second_choice=p.choice2             # Final choice made
                        )
                    }

                return response

        # Default response - echo back any unhandled data to all players
        return {p.id_in_group: data for p in group.get_players()}

    @staticmethod
    def display_remaining_images(player, players):
        """
        Helper method to prepare the display of other players' choices
        Creates a response showing what images each player chose
        """
        response = {}
        for p in players:
            other_players = p.get_others_in_group()
            all_images = {}
            for op in other_players:
                # Use transparent version for computer choices, regular for manual choices
                chosen_image = op.chosen_image_computer if op.chosen_image_computer else op.chosen_image_one
                all_images[op.id_in_group] = f'main_task/{chosen_image}'
            response[p.id_in_group] = dict(
                display_all_images=True,
                all_images=all_images
            )
        
        return response

    @staticmethod
    def after_all_players_arrive(group: Group):
        """
        Called after all players have completed the round
        Finalizes payoffs for the group
        """
        group.set_payoffs()

# -------------------------------------------------------------------------------------------------------------------- #
# ---- FINAL RESULTS PAGE: AFTER 80 ROUNDS, PLAYERS RECEIVE THEIR POINTS TALLY ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class FinalResults(Page):

    # is_displayed method is used to determine when this page should be shown
    # In this case, FinalResults is only shown after the last round
    @staticmethod
    def is_displayed(player: Player):
        # Only show this page after the last round
        return player.round_number == C.NUM_ROUNDS

    # vars_for_template method is used to pass variables to the template
    # This is used to calculate and display the final results to the player
    @staticmethod
    def vars_for_template(player: Player):
        log_query_count("Final Results - Total queries across all rounds")

        # Calculate final payments efficiently
        player.calculate_payoffs()

        # Get final round data efficiently
        final_round = player.in_round(C.NUM_ROUNDS)
        final_bonus_score = final_round.bonus_payment_score
        final_choice1_sum = final_round.choice1_sum_earnings

        # Prepare CSV data
        column_names = [
            'Prolific ID',
            'Total Payoff'
        ]

        data = [
            player.participant.vars.get('prolific_id', 'Unknown'),
            float(player.total_payoff)
        ]
        
        file_exists = os.path.isfile('payoffs.csv')
        
        with open('payoffs.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(column_names)
            writer.writerow(data)
        
        return {
            'choice2_sum_earnings': player.choice2_sum_earnings,
            'bonus_payment_score': final_bonus_score,
            'choice1_sum_earnings': final_choice1_sum,
            'player_id': player.id_in_group,
            'base_payoff': player.base_payoff,
            'bonus_payoff': player.bonus_payoff,
            'total_payoff': player.total_payoff,
        }

    # app_after_this_page method is used to redirect players to the next app
    # In this case, players will be directed to the submission app after seeing their results
    @staticmethod
    def app_after_this_page(player, upcoming_apps):

        # Debug print to see what apps are coming next
        print('upcoming_apps is', upcoming_apps)

        # Direct players to the submission app after showing results
        return "submission"  # Hardcoded name of the last app

# Define the sequence of pages that players will see
# Players first see the main task page (MyPage) for each round,
# then see the final results page (FinalResults) after all rounds are complete

from .tests import PlayerBot # Import the PlayerBot class from the tests.py file

page_sequence = [WaitPage2, TransitionToMainTask, MyPage, FinalResults]  

# -------------------------------------------------------------------------------------------------------------------- #