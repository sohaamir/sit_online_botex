# practice_task/__init__.py

from otree.api import *
from . import *
import random
import time
import csv
from otree.api import Submission, WaitPage
import threading
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

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

    print(f"Reversal rounds: {reversal_rounds}")
    return sequence, reversal_rounds

# -------------------------------------------------------------------------------------------------------------------- #
# ---- REWARD SEQUENCE: GENERATE A SEQUENCE OF REWARDS FOR THE EXPERIMENT BASED ON THE NUMBER OF ROUNDS ------ #

# Define the core parameters of the experiment
NUM_ROUNDS = 4  # Total number of rounds in the experiment
REWARD_PROBABILITY_A = 0.9  # 90% chance of reward for option A when it's the high-probability option
REWARD_PROBABILITY_B = 0.1  # 10% chance of reward for option A when it's the low-probability option

# This function generates a win for the high probability image in each of the rounds (i.e., no reversals)
def generate_reward_sequence(num_rounds, reversal_rounds):
    sequence = []
    current_high_prob_image = 'A'  # Start with image A as high probability
    
    # Prepare CSV file headers for logging the reward sequence
    csv_data = [['Round', 'High Prob', 'reward_A', 'reward_B']]

    print("\nGenerated Reward Sequence:")
    print("Round | High Prob | reward_A | reward_B")
    print("------|-----------|----------|----------")

    # Generate rewards for each round
    for round_num in range(1, num_rounds + 1):
        # Always set reward_A to 1 and reward_B to 0
        reward_A = 1
        reward_B = 0

        sequence.append((reward_A, reward_B))
        print(f"{round_num:5d} | {current_high_prob_image:9s} | {reward_A:8d} | {reward_B:8d}")
        csv_data.append([round_num, current_high_prob_image, reward_A, reward_B])

    # Calculate and display statistics
    print("\nReward Statistics:")
    print(f"High probability rewards: {num_rounds}/{num_rounds} (100.00%)")
    print(f"Low probability rewards: 0/{num_rounds} (0.00%)")

    return sequence

# Generate all sequences needed for the experiment when this module is first imported
TRIAL_SEQUENCE, REVERSAL_ROUNDS = generate_trial_sequence()
REWARD_SEQUENCE = generate_reward_sequence(4, REVERSAL_ROUNDS)

# -------------------------------------------------------------------------------------------------------------------- #
# Base Constants: Used to define constants across all pages and subsessions in the game
# This class defines the fundamental parameters and settings that will be used throughout the experiment

class C(BaseConstants):
    # URL path for accessing this task in the browser
    NAME_IN_URL = 'practice_task'
    
    # Number of players that form a group in the experiment
    PLAYERS_PER_GROUP = 5
    
    # Total number of rounds in the experiment (defined earlier as 4)
    NUM_ROUNDS = NUM_ROUNDS
    
    # The reward probabilities for each option
    # When an option is in its "high probability" state, it has a 90% chance of giving a reward
    # When an option is in its "low probability" state, it has a 10% chance of giving a reward
    REWARD_PROBABILITY_A = REWARD_PROBABILITY_A
    REWARD_PROBABILITY_B = REWARD_PROBABILITY_B
    
    # The image files that represent the two choice options players can select between
    IMAGES = ['option1A.bmp', 'option1B.bmp']
    
    # The avatar image used to represent players in the interface
    AVATAR_IMAGE = 'practice_task/avatar_male.png'
    
    # Dictionary mapping image names to their full file paths in the static directory
    # Includes both regular images and transparent versions (with '_tr' suffix)
    IMAGE_PATHS = {
        'option1A.bmp': '_static/practice_task/option1A.bmp',
        'option1B.bmp': '_static/practice_task/option1B.bmp',
        'option1A_tr.bmp': '_static/practice_task/option1A_tr.bmp',
        'option1B_tr.bmp': '_static/practice_task/option1B_tr.bmp',
        'avatar_male.png': '_static/practice_task/avatar_male.png',
    }
    
    # The pre-generated sequence of rewards that will be used throughout the experiment
    REWARD_SEQUENCE = REWARD_SEQUENCE

# -------------------------------------------------------------------------------------------------------------------- #
# ---- SUBSESSIONS: USED TO DEFINE THE ROUNDS FOR REVERSAL AND BOTS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# A subsession represents one round of the game

class Subsession(BaseSubsession):

    # This method groups players together based on their arrival time
    def group_by_arrival_time_method(self, waiting_players):
        if len(waiting_players) >= C.PLAYERS_PER_GROUP:
            return waiting_players[:C.PLAYERS_PER_GROUP]
        return None

    def creating_session(self):
        if self.round_number > 1:
            self.group_like_round(1)  # Keep same groups as round 1
            for group in self.get_groups():
                group.round_reward_set = False
                
            for player in self.get_players():
                if hasattr(player, 'last_connection_time'):
                    time_since_connection = time.time() - player.last_connection_time
                    if time_since_connection > 10:
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
    current_round = models.IntegerField(initial=1)      # Tracks the current round number
    my_page_load_time = models.FloatField()            # Records when the page loads for the group
    round_reward_A = models.IntegerField()             # Reward for option A in current round
    round_reward_B = models.IntegerField()             # Reward for option B in current round
    intertrial_interval = models.IntegerField(initial=0)  # Time gap between trials (3000-4000ms)
    
    # Control flags for timing and state management
    second_bet_timer_ended_executed = models.BooleanField(initial=False)  # Tracks if second betting phase has ended
    next_round_transition_time = models.FloatField()    # When to transition to next round
    
    # Probability settings for the two options
    reward_probability_A = models.FloatField(initial=0.9)  # Starting probability for option A
    reward_probability_B = models.FloatField(initial=0.1)  # Starting probability for option B
    
    # Track which image has which probability
    seventy_percent_image = models.StringField(initial='option1A.bmp')  # Image with 90% reward chance
    thirty_percent_image = models.StringField(initial='option1B.bmp')   # Image with 10% reward chance
    
    # State tracking variables
    reversal_rounds = models.StringField(initial='')    # Records when probability reversals occur
    bet_container_displayed = models.BooleanField(initial=False)  # Whether betting UI is shown
    remaining_images_displayed = models.BooleanField(initial=False)  # Whether all choices are displayed
    reversal_happened = models.BooleanField(initial=False)  # If a probability reversal occurred this round
    round_reward_set = models.BooleanField(initial=False)  # If rewards have been set for this round
    
    # Page loading coordination
    all_players_loaded = models.BooleanField(initial=False)  # If all players have loaded the page
    players_loaded_count = models.IntegerField(initial=0)    # Number of players who have loaded
    disconnected_players = models.StringField(initial="")
    bot_players = models.StringField(initial="")
    active_bots = models.StringField(initial="")

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
        # Find data for current round in the pre-generated sequence
        current_round_data = next((item for item in TRIAL_SEQUENCE if item[0] == self.round_number), None)
        
        if current_round_data:
            # Set which image has high probability for this round
            self.seventy_percent_image = current_round_data[1]
            self.thirty_percent_image = 'option1B.bmp' if self.seventy_percent_image == 'option1A.bmp' else 'option1A.bmp'
            previous_round = self.in_round(self.round_number - 1) if self.round_number > 1 else None

            # Mark if this is a reversal round
            if self.round_number in REVERSAL_ROUNDS:
                self.reversal_happened = True
            else:
                self.reversal_happened = False

            # Set probabilities based on which image has high probability
            if self.seventy_percent_image == 'option1A.bmp':
                self.reward_probability_A = 0.9
                self.reward_probability_B = 0.1
            else:
                self.reward_probability_A = 0.1
                self.reward_probability_B = 0.9

        print(f"Round {self.round_number}: 90% image is {self.seventy_percent_image}, 10% image is {self.thirty_percent_image}")
        print(f"Current probabilities: option1A.bmp - {self.reward_probability_A}, option1B.bmp - {self.reward_probability_B}")

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
    chosen_image_one = models.StringField()              # Actual image chosen in first choice
    chosen_image_one_binary = models.IntegerField()      # First choice coded as 1 or 2
    chosen_image_two = models.StringField(initial=None)  # Actual image chosen in second choice
    chosen_image_two_binary = models.IntegerField()      # Second choice coded as 1 or 2
    
    # Computer choice tracking
    chosen_image_computer = models.StringField(initial='')     # Image chosen by computer for first choice
    chosen_image_computer_two = models.StringField(initial='') # Image chosen by computer for second choice
    
    # Timing variables
    my_page_load_time = models.FloatField()             # When page loaded for this player
    individual_page_load_time = models.FloatField()      # Individual timing for page load
    initial_choice_time = models.FloatField()            # Time taken for first choice
    initial_bet_time = models.FloatField()               # Time taken for first bet
    second_choice_time = models.FloatField()             # Time taken for second choice
    second_bet_time = models.FloatField()                # Time taken for second bet
    
    # Earnings tracking
    choice2_earnings = models.IntegerField(initial=0)    # Points earned from second choice
    choice2_sum_earnings = models.IntegerField(initial=0) # Cumulative earnings from second choices
    
    # Final payment calculations
    total_payoff = models.CurrencyField(initial=0)      # Total payment (base + bonus)
    
    # Outcome tracking
    loss_or_gain = models.IntegerField()                # Whether player gained (1) or lost (-1) points
    
    # Computer intervention flags
    computer_choice_one = models.BooleanField(initial=True)   # If computer made first choice
    computer_bet_one = models.BooleanField(initial=False)     # If computer made first bet
    computer_choice_two = models.BooleanField(initial=True)   # If computer made second choice
    computer_bet_two = models.BooleanField(initial=False)     # If computer made second bet
    
    # Track if second choice was made manually
    manual_second_choice = models.BooleanField(initial=False)

    # Connection tracking fields
    disconnection_streak = models.IntegerField(initial=0)
    is_bot = models.BooleanField(initial=False)
    last_connection_time = models.FloatField(initial=0)

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
            if old_streak > 0:
                logging.info(f"Player {self.id_in_group} streak reset from {old_streak} to 0 "
                            f"(connected for {time_since_disconnect:.1f}s)")
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

# -------------------------------------------------------------------------------------------------------------------- #
# ---- PAGES: DEFINE THE PAGES USED IN THE GAME INCLUDING WAITING ROOMS, TASKS AND RESULTS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class WaitPage1(WaitPage):
    template_name = 'practice_task/WaitPage1.html'
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

class TransitionToPracticeTask(Page):
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
        # Set page timeout to 42 seconds (4200 milliseconds)
        return 4200

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

        # Process both first and second choices/bets using the same logic
        # This loop handles two sets of fields: first choice/bet and second choice/bet
        for choice_field, computer_choice_field, bet_field, image_field in [
            ('choice1', 'computer_choice1', 'bet1', 'chosen_image_one'),
            ('choice2', 'computer_choice2', 'bet2', 'chosen_image_two')
        ]:
            # Get the player's manual choice and any computer-made choice
            manual_choice = player.field_maybe_none(choice_field)
            computer_choice = player.field_maybe_none(computer_choice_field)

            # Decision tree for handling choices:
            # 1. If there's a valid manual choice but no valid computer choice, keep manual choice
            if manual_choice is not None and (computer_choice is None or computer_choice not in ['left', 'right']):
                pass  # Keep the manual choice

            # 2. If there's a valid computer choice, use it instead
            elif computer_choice in ['left', 'right']:
                setattr(player, choice_field, None)
                setattr(player, computer_choice_field, computer_choice)
                
            # 3. If neither choice is valid, explicitly set both to None
            elif manual_choice is None and computer_choice is None:
                setattr(player, choice_field, None)
                setattr(player, computer_choice_field, None)

            # Determine which choice (manual or computer) to use as the final choice
            final_choice = getattr(player, computer_choice_field) or getattr(player, choice_field)

            # Convert the left/right choice into the actual image chosen
            if final_choice in ['left', 'right']:
                chosen_image = player.left_image if final_choice == 'left' else player.right_image
                # Save the chosen image both in the player model and participant variables
                setattr(player, image_field, chosen_image)
                player.participant.vars[image_field] = chosen_image
            else:
                # If no valid choice was made, set chosen image to None
                setattr(player, image_field, None)
                player.participant.vars[image_field] = None

            # Set default bet of 1 if no bet was made
            bet_value = player.field_maybe_none(bet_field)
            if bet_value is None:
                setattr(player, bet_field, 1)

        # Calculate earnings for both choices
        player.choice2_earnings = player.bet2 * 20 * player.trial_reward if player.trial_reward == 1 else -1 * player.bet2 * 20

        # Handle first round differently since there's no previous round to reference
        if player.round_number == 1:
            player.choice2_sum_earnings = player.choice2_earnings
        else:
            # Add current round earnings to previous totals
            previous_player = player.in_round(player.round_number - 1)
            player.choice2_sum_earnings = previous_player.choice2_sum_earnings + player.choice2_earnings

    # vars_for_template method is used to pass variables to the template
    # This is used to display information to the player in the interface
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        # At the start of each round, check all players' connection status
        for p in group.get_players():
            current_streak = p.field_maybe_none('disconnection_streak')
            if current_streak is not None and current_streak > 0:
                logging.info(f"Start of round {group.round_number}: Player {p.id_in_group} has streak of {current_streak}/5")
                # If they're already at or past threshold, ensure bot is active
                if current_streak >= 5 and not p.is_bot:
                    p.increment_disconnect_streak()
        
        # Initialize connection tracking for new rounds
        player.last_connection_time = time.time()

        # Randomly determine which image appears on left/right for each player for each round
        try:
            images = C.IMAGES.copy()
            random.shuffle(images)
            left_image = images[0]
            right_image = images[1]
            # Initialize both fields explicitly 
            player.left_image = left_image
            player.right_image = right_image

        except Exception as e:
            logging.error(f"Failed to set images for player {player.id_in_group}: {e}")
            # Provide fallback values
            left_image = 'option1A.bmp'
            right_image = 'option1B.bmp'
            player.left_image = left_image 
            player.right_image = right_image

        # Get other_players before using it
        other_players = player.get_others_in_group()

        return {
            'left_image': f'practice_task/{left_image}',
            'right_image': f'practice_task/{right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': [p.id_in_group for p in other_players],
            'chosen_images': {p.id_in_group: f"practice_task/{p.field_maybe_none('chosen_image_computer') or p.field_maybe_none('chosen_image_one') or 'default_image.png'}" for p in group.get_players()},
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
                if random.random() < 0.05:  # Log activity occasionally (5% of checks)
                    logging.info(f"Activity recorded for player {player.id_in_group}")
            except Exception as e:
                logging.error(f"Error recording activity for player {player.id_in_group}: {e}")
            return

        # Handle connection checks
        if 'check_connection' in data:
            try:
                current_time = time.time()
                last_disconnect = player.participant.vars.get('last_disconnect_time', 0)
                last_activity = player.participant.vars.get('last_activity_time', current_time)
                time_since_disconnect = current_time - last_disconnect
                time_since_activity = data.get('time_since_activity', 0) / 1000  # Convert ms to seconds
                
                # Update connection time
                player.last_connection_time = current_time
                
                # Process connection status
                if time_since_activity > 15:  # If inactive for over 15 seconds
                    if time_since_disconnect > 10:  # And disconnected for over 10 seconds
                        player.increment_disconnect_streak()
                else:
                    # Only reset streak if properly connected for a while
                    if time_since_disconnect >= 20:
                        player.reset_disconnect_streak()
                        
                # Detailed logging (5% of checks)
                if random.random() < 0.05:
                    current_streak = player.field_maybe_none('disconnection_streak') or 0
            except Exception as e:
                logging.error(f"Error processing connection check for player {player.id_in_group}: {e}")
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

        if 'my_page_load_time' in data:
            # Convert and record load times for individual player
            player.my_page_load_time = round(data['my_page_load_time'] / 1000, 2)
            player.individual_page_load_time = round(data['individual_page_load_time'] / 1000, 2)
            
            # Track number of players who have loaded the page
            if not player.field_maybe_none('my_page_load_time'):
                group.players_loaded_count += 1
            
            # Send acknowledgment to client
            response = {player.id_in_group: dict(acknowledged=True)}
            
            # When all players are ready, start the game
            if group.players_loaded_count == C.PLAYERS_PER_GROUP:
                group.my_page_load_time = round(max(p.my_page_load_time for p in players), 2)
                group.set_round_reward()  # Set up rewards for this round
                group.reversal_learning()  # Handle probability reversals
                return {p.id_in_group: dict(start_choice_phase_timer=True) for p in players}
            
            return response

        # ---- FIRST CHOICE PHASE ----
        # Handle player's first choice and timing

        if 'initial_choice_time' in data:
            # Calculate and record how long the player took to make their choice
            if data['initial_choice_time'] is not None:
                actual_choice_time = round((data['initial_choice_time'] - player.individual_page_load_time) / 1000, 2)
                player.initial_choice_time = min(actual_choice_time, 3.0)  # Cap at 3 seconds
            else:
                player.initial_choice_time = 3.0

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
                            p.initial_choice_time = 3.0
                            
                            # Handle binary coding and image selection
                            try:
                                p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 2
                                p.computer_choice_one = True
                                
                                # Use transparent version of image for computer choices
                                if p.chosen_image_one == 'option1A.bmp':
                                    p.chosen_image_computer = 'option1A_tr.bmp'
                                elif p.chosen_image_one == 'option1B.bmp':
                                    p.chosen_image_computer = 'option1B_tr.bmp'
                                    
                            except Exception as e:
                                logging.error(f"Error processing computer choice details for player {p.id_in_group}: {e}")
                                # Set fallback values
                                p.chosen_image_one_binary = 1
                                p.computer_choice_one = True
                                p.chosen_image_computer = 'option1A_tr.bmp'
                                
                        else:
                            # Record binary coding for manual choices
                            try:
                                p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 2
                            except Exception as e:
                                logging.error(f"Error processing manual choice details for player {p.id_in_group}: {e}")
                                p.chosen_image_one_binary = 1
                            
                    except Exception as e:
                        logging.error(f"Error processing choice for player {p.id_in_group}: {e}")
                        # Set safe fallback values
                        p.choice1 = 'left'
                        p.computer_choice1 = 'left'
                        p.chosen_image_one = C.IMAGES[0]
                        p.chosen_image_one_binary = 1
                        p.computer_choice_one = True

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
                    p.initial_bet_time = 3.0
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
            print(f"Received manual second choice for player {player.id_in_group}")
            
            # Record player's second choice
            player.choice2 = data['second_choice']
            player.chosen_image_two = player.left_image if data['second_choice'] == 'left' else player.right_image
            player.participant.vars['chosen_image_two'] = player.chosen_image_two
            player.computer_choice_two = False
            player.manual_second_choice = True
            player.second_choice_time = round(data['second_choice_time'] / 1000, 2)
            player.chosen_image_two_binary = 1 if player.chosen_image_two == 'option1A.bmp' else 2
            player.chosen_image_computer_two = ''
            player.computer_choice2 = ''
            
            return {player.id_in_group: dict(highlight_selected_second_choice=player.choice2)}

        # Handle second choice timer expiration
        if 'second_choice_timer_ended' in data:
            # Process computer choices for players who didn't respond
            for p in players:
                if not p.field_maybe_none('choice2'):
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
                else:
                    print(f"Warning: chosen_image_two is None for player {p.id_in_group}")

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

                # Assign computer bets if needed
                for p in players:
                    if p.bet2 == 0:
                        random_bet = random.randint(1, 3)
                        p.bet2 = random_bet
                        p.bet2 = p.bet2
                        p.computer_bet_two = True
                        p.second_bet_time = 3.0
                        response[p.id_in_group] = dict(highlight_computer_second_bet=p.bet2)

                # Calculate final results for the round
                group.set_round_reward()
                group.calculate_player_rewards()

                # Calculate earnings for all players
                for p in players:
                    p.choice2_earnings = p.bet2 * 20 * p.trial_reward if p.trial_reward == 1 else -1 * p.bet2 * 20
                    p.choice2_sum_earnings = sum([prev_player.choice2_earnings for prev_player in p.in_previous_rounds()]) + p.choice2_earnings
                    p.loss_or_gain = -1 if p.choice2_earnings < 0 else 1

                # Generate random delay before next round
                group.generate_intertrial_interval()
                group.next_round_transition_time = time.time() * 1000 + group.intertrial_interval

                # Prepare final display information
                # Create dictionaries mapping player IDs to their chosen images and win/loss status
                chosen_images_secondchoicepage = {
                    p.id_in_group: f"practice_task/{p.chosen_image_computer_two if p.computer_choice_two else p.chosen_image_two}" 
                    for p in players
                }
                win_loss_images = {p.id_in_group: f'practice_task/{"win" if p.trial_reward == 1 else "loss"}.png' for p in players}

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
                all_images[op.id_in_group] = f'practice_task/{chosen_image}'
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
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'choice2_sum_earnings': player.choice2_sum_earnings,
            'player_id': player.id_in_group,
        }
    
# -------------------------------------------------------------------------------------------------------------------- #
# ---- MAIN TASK INSTRUCTIONS: DISPLAYED ON THE LAST ROUND BEFORE MAIN TASK ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class MainTaskInstructions(Page):
    @staticmethod 
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS  # Only show on last round

    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        return "main_task"  # Direct to main task after this page

from .tests import PlayerBot

page_sequence = [WaitPage1, TransitionToPracticeTask, MyPage, FinalResults, MainTaskInstructions]

# -------------------------------------------------------------------------------------------------------------------- #