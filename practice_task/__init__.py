# practice_task/__init__.py

# The practice task could be made a lot simpler, but I just copied the infrastructure from the main task as it had
# a lot of features that I wanted to keep (e.g., with players dropping out, phase timings etc.)
#
# The main differences are that:
# 1. The practice task only has 5 rounds, and does not include reversals
# 2. They play against computer agents who always make the same choices
# 3. A different set of images are used
# 4. Players have 6 seconds to make their choices and bets instead of 3 seconds in the main task


from otree.api import Submission, WaitPage
from otree.api import *
import threading
import logging
from . import *
import random
import json
import time
import csv

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
This is the practice task for the experiment. Players will make choices and bets on two options in each round (five rounds total). 
The reward contingencies are fixed as are the choices by the other players, represented by computer agents.
"""

# -------------------------------------------------------------------------------------------------------------------- #
# ---- CONSTANTS: DEFINE CONSTANTS USED IN THE GAME INCLUDING NUMBER OF PLAYERS, ROUNDS AND TRIAL SEQUENCE------ #
# -------------------------------------------------------------------------------------------------------------------- #

# ---- REWARD SEQUENCE: GENERATE A SEQUENCE OF REWARDS FOR THE EXPERIMENT BASED ON THE NUMBER OF ROUNDS ------ #

# Define the core parameters of the experiment
NUM_ROUNDS = 5  # Total number of rounds in the experiment

# This function generates a win for the high probability image in each of the rounds (i.e., no reversals)
def generate_reward_sequence(num_rounds):
    sequence = []
    print("\nGenerated Reward Sequence:")
    print("Round | reward_A | reward_B")
    print("------|----------|----------")

    for round_num in range(1, num_rounds + 1):
        if round_num <= 3:
            reward_A = 1
            reward_B = 0
        else:
            reward_A = 0
            reward_B = 1
        
        sequence.append((reward_A, reward_B))
        print(f"{round_num:5d} | {reward_A:8d} | {reward_B:8d}")
    
    return sequence

# Generate all sequences needed for the experiment when this module is first imported
REWARD_SEQUENCE = generate_reward_sequence(NUM_ROUNDS)

# -------------------------------------------------------------------------------------------------------------------- #
# Base Constants: Used to define constants across all pages and subsessions in the game
# This class defines the fundamental parameters and settings that will be used throughout the experiment

class C(BaseConstants):
    # URL path for accessing this task in the browser
    NAME_IN_URL = 'practice_task'
    
    # Groups of 1 player each 
    # oTree throws up a warning that this is set to 1, but it's more of a 'best practice', the code works fine
    PLAYERS_PER_GROUP = None
    
    # Total number of rounds in the experiment (defined earlier as 5)
    NUM_ROUNDS = NUM_ROUNDS
    
    # The image files that represent the two choice options players can select between
    IMAGES = ['option1A.bmp', 'option1B.bmp']
    
    # The avatar image used to represent players in the interface
    AVATAR_IMAGE = 'practice_task/avatar_male.png'
    
    # Dictionary mapping image names to their full file paths in the static directory
    # Importantly, we do not have transparent images, since we are using computer agents who always make choices

    IMAGE_PATHS = {
        'option1A.bmp': '_static/practice_task/option1A.bmp',
        'option1B.bmp': '_static/practice_task/option1B.bmp',
        'option1A_tr.bmp': '_static/practice_task/option1A.bmp',
        'option1B_tr.bmp': '_static/practice_task/option1B.bmp',
        'avatar_male.png': '_static/practice_task/avatar_male.png',
    }
    
    # The pre-generated sequence of rewards that will be used throughout the experiment
    REWARD_SEQUENCE = REWARD_SEQUENCE

# -------------------------------------------------------------------------------------------------------------------- #
# ---- SUBSESSIONS: USED TO GROUP PLAYERS AND DEFINE THE BOTS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# A subsession represents one round of the game

class Subsession(BaseSubsession):

    # This method groups players together based on their arrival time
    def group_by_arrival_time_method(self, waiting_players):
        # Form a group as soon as one player arrives
        if len(waiting_players) >= 1:
            return [waiting_players[0]]
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
    
    # State tracking variables
    bet_container_displayed = models.BooleanField(initial=False)  # Whether betting UI is shown
    remaining_images_displayed = models.BooleanField(initial=False)  # Whether all choices are displayed
    round_reward_set = models.BooleanField(initial=False)  # If rewards have been set for this round
    
    # Page loading coordination
    all_players_loaded = models.BooleanField(initial=False)  # If all players have loaded the page
    players_loaded_count = models.IntegerField(initial=0)    # Number of players who have loaded
    disconnected_players = models.StringField(initial="")
    bot_players = models.StringField(initial="")
    active_bots = models.StringField(initial="")

    # Add tracking for computer player choices
    computer_player_choices = models.StringField(initial="")  # JSON string to store choices
    computer_player_bets = models.StringField(initial="")  # JSON string to store bets

#### ---------------- Define the computer choices ------------------------ ####
# This method generates choices for the computer players
# The computer players will make choices and bets simulating the other 4 players in the group

    def generate_computer_choices(self):
        """Generate choices for the computer players"""
        
        # Create 4 computer players with IDs 2-5
        computer_players = {
            str(i): {
                'choice1': random.choice(['left', 'right']),
                'bet1': random.randint(1, 3),
                'choice2': random.choice(['left', 'right']),
                'bet2': random.randint(1, 3),
                'chosen_image_one': '',
                'chosen_image_two': '',
                'computer_choice_one': True,
                'computer_choice_two': True,
                'computer_bet_one': True,
                'computer_bet_two': True,
                'trial_reward': 0
            } for i in range(2, 6)
        }
        
        self.computer_player_choices = json.dumps(computer_players)
        
        # Calculate chosen images based on left/right choices
        real_player = self.get_player_by_id(1)
        for player_id, data in computer_players.items():
            # For first choice
            if data['choice1'] == 'left':
                data['chosen_image_one'] = real_player.left_image
                data['chosen_image_computer'] = real_player.left_image.replace('.bmp', '.bmp')
            else:
                data['chosen_image_one'] = real_player.right_image
                data['chosen_image_computer'] = real_player.right_image.replace('.bmp', '.bmp')
                
            # For second choice
            if data['choice2'] == 'left':
                data['chosen_image_two'] = real_player.left_image
                data['chosen_image_computer_two'] = real_player.left_image.replace('.bmp', '.bmp')
            else:
                data['chosen_image_two'] = real_player.right_image
                data['chosen_image_computer_two'] = real_player.right_image.replace('.bmp', '.bmp')
                
        self.computer_player_choices = json.dumps(computer_players)

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
        if not self.round_reward_set:
            self.round_reward_A, self.round_reward_B = C.REWARD_SEQUENCE[self.round_number - 1]
            self.round_reward_set = True
            print(f"Round {self.round_number}: reward_A = {self.round_reward_A}, reward_B = {self.round_reward_B}")

    def calculate_player_rewards(self):
        # Get the real player
        player = self.get_player_by_id(1)
        
        # Calculate reward for real player based on their second choice
        if player.field_maybe_none('chosen_image_two') is not None:
            if player.chosen_image_two == 'option1A.bmp':
                player.trial_reward = self.round_reward_A
            else:
                player.trial_reward = self.round_reward_B
        
        # For computer players, calculate in their separate storage
        if self.field_maybe_none('computer_player_choices'):
            computer_players = json.loads(self.computer_player_choices)
            for player_id, data in computer_players.items():
                # Skip if no second choice
                if 'chosen_image_two' not in data or not data['chosen_image_two']:
                    continue
                    
                # Calculate reward based on chosen image
                if data['chosen_image_two'] == 'option1A.bmp':
                    data['trial_reward'] = self.round_reward_A
                else:
                    data['trial_reward'] = self.round_reward_B
                    
            # Save updated computer players data
            self.computer_player_choices = json.dumps(computer_players)

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

# Group players together in the WaitPage which they don't see because they are automatically grouped
class GroupingWaitPage(WaitPage):
    group_by_arrival_time = True

# Transition to the practice task
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

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        # Initialize connection tracking for new rounds
        player.last_connection_time = time.time()

        # Randomly determine which image appears on left/right for the player
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

        # Create four virtual players with IDs 2-5
        virtual_player_ids = list(range(2, 6))
        
        # Initialize computer choices if not already done
        if not group.field_maybe_none('computer_player_choices'):
            # Generate initial random choices for computer players
            import json
            computer_players = {
                str(i): {
                    'choice1': random.choice(['left', 'right']),
                    'bet1': random.randint(1, 3),
                    'choice2': random.choice(['left', 'right']),
                    'bet2': random.randint(1, 3),
                    'chosen_image_one': '',
                    'chosen_image_computer': '',
                    'chosen_image_two': '',
                    'chosen_image_computer_two': '',
                    'computer_choice_one': True,
                    'computer_choice_two': True,
                    'trial_reward': 0
                } for i in virtual_player_ids
            }
            
            # Determine chosen images based on choices and player's image assignment
            for player_id, data in computer_players.items():
                # First choice images
                data['chosen_image_one'] = left_image if data['choice1'] == 'left' else right_image
                data['chosen_image_computer'] = (left_image if data['choice1'] == 'left' else right_image).replace('.bmp', '.bmp')
                
                # Second choice images  
                data['chosen_image_two'] = left_image if data['choice2'] == 'left' else right_image
                data['chosen_image_computer_two'] = (left_image if data['choice2'] == 'left' else right_image).replace('.bmp', '.bmp')
            
            group.computer_player_choices = json.dumps(computer_players)
        
        # Create chosen_images dictionary (init with placeholder images)
        chosen_images = {player.id_in_group: f"practice_task/{player.field_maybe_none('chosen_image_computer') or player.field_maybe_none('chosen_image_one') or 'default_image.png'}"}
        
        # Add placeholder images for virtual players
        for virtual_id in virtual_player_ids:
            chosen_images[virtual_id] = f"practice_task/default_image.png"

        return {
            'left_image': f'practice_task/{left_image}',
            'right_image': f'practice_task/{right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': virtual_player_ids,
            'chosen_images': chosen_images,
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
        
        # Initialize response dictionary and get reference to group
        group = player.group
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
        if 'my_page_load_time' in data:
            # Convert and record load times for player
            player.my_page_load_time = round(data['my_page_load_time'] / 1000, 2)
            player.individual_page_load_time = round(data['individual_page_load_time'] / 1000, 2)
            
            # With single-player, we can immediately start
            group.players_loaded_count = 1
            group.my_page_load_time = player.my_page_load_time
            
            # Send acknowledgment to client
            response = {player.id_in_group: dict(acknowledged=True)}
            
            # Set up the round
            group.set_round_reward()  # Set up rewards for this round
            
            # If computer player choices haven't been generated yet, do it now
            if not group.field_maybe_none('computer_player_choices'):
                # Initialize computer players' choices
                computer_players = {
                    str(i): {
                        'choice1': random.choice(['left', 'right']),
                        'bet1': random.randint(1, 3),
                        'choice2': random.choice(['left', 'right']),
                        'bet2': random.randint(1, 3),
                        'chosen_image_one': '',
                        'chosen_image_computer': '',
                        'chosen_image_two': '',
                        'chosen_image_computer_two': '',
                        'computer_choice_one': True,
                        'computer_choice_two': True,
                        'trial_reward': 0
                    } for i in range(2, 6)
                }
                
                # Calculate chosen images based on left/right choices
                for player_id, data in computer_players.items():
                    # First choice images
                    data['chosen_image_one'] = player.left_image if data['choice1'] == 'left' else player.right_image
                    data['chosen_image_computer'] = (player.left_image if data['choice1'] == 'left' else player.right_image).replace('.bmp', '.bmp')
                    
                    # Second choice images
                    data['chosen_image_two'] = player.left_image if data['choice2'] == 'left' else player.right_image
                    data['chosen_image_computer_two'] = (player.left_image if data['choice2'] == 'left' else player.right_image).replace('.bmp', '.bmp')
                
                group.computer_player_choices = json.dumps(computer_players)
                
            # Start the choice phase for the real player
            return {player.id_in_group: dict(start_choice_phase_timer=True)}
            
        # ---- FIRST CHOICE PHASE ----
        if 'initial_choice_time' in data:
            # Calculate and record how long the player took to make their choice
            if data['initial_choice_time'] is not None:
                actual_choice_time = round((data['initial_choice_time'] - player.individual_page_load_time) / 1000, 2)
                player.initial_choice_time = min(actual_choice_time, 6.0)  # Cap at 6 seconds
            else:
                player.initial_choice_time = 6.0

            # Record player's manual choice if made
            if 'choice' in data and not player.field_maybe_none('chosen_image_one'):
                player.choice1 = data['choice']
                player.chosen_image_one = player.left_image if data['choice'] == 'left' else player.right_image
                player.participant.vars['chosen_image_one'] = player.chosen_image_one
                player.computer_choice_one = False  # Mark as manual choice

        # ---- CHOICE TIMER END PHASE ----
        if 'choice_phase_timer_ended' in data:
            try:
                # If player hasn't made a choice, computer makes one
                if player.field_maybe_none('choice1') is None or player.choice1 == '':
                    # Ensure valid image fields exist
                    left_img = player.field_maybe_none('left_image')
                    right_img = player.field_maybe_none('right_image')
                    
                    if left_img is None:
                        left_img = C.IMAGES[0]
                        player.left_image = left_img
                    if right_img is None:
                        right_img = C.IMAGES[1]
                        player.right_image = right_img
                        
                    random_choice = random.choice(['left', 'right'])
                    
                    # Record computer's choice
                    player.choice1 = random_choice
                    player.computer_choice1 = random_choice
                    player.chosen_image_one = left_img if random_choice == 'left' else right_img
                    player.participant.vars['chosen_image_one'] = player.chosen_image_one
                    player.initial_choice_time = 6.0
                    
                    # Handle binary coding and image selection
                    player.chosen_image_one_binary = 1 if player.chosen_image_one == 'option1A.bmp' else 2
                    player.computer_choice_one = True
                    
                    # Use transparent version of image for computer choices
                    if player.chosen_image_one == 'option1A.bmp':
                        player.chosen_image_computer = 'option1A.bmp'
                    elif player.chosen_image_one == 'option1B.bmp':
                        player.chosen_image_computer = 'option1B.bmp'
                else:
                    # Record binary coding for manual choices
                    player.chosen_image_one_binary = 1 if player.chosen_image_one == 'option1A.bmp' else 2
                    
                # Move to betting phase
                return {player.id_in_group: dict(
                    show_bet_container=True, 
                    start_bet_timer=True, 
                    highlight_selected_choice=player.field_maybe_none('choice1') or 'left'
                )}
                    
            except Exception as e:
                logging.error(f"Critical error in choice phase timer end: {e}")
                # Provide safe fallback response to keep game running
                return {player.id_in_group: dict(
                    show_bet_container=True,
                    start_bet_timer=True,
                    highlight_selected_choice='left'
                )}

        # ---- FIRST BET PHASE ----
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
            
            # Assign computer bet if needed
            if not player.field_maybe_none('bet1') and not player.computer_bet_one:
                random_bet = random.randint(1, 3)
                player.bet1 = random_bet
                player.participant.vars['bet1'] = player.bet1
                player.initial_bet_time = 6.0
                player.computer_bet_one = True
                response[player.id_in_group] = dict(highlight_computer_bet=player.bet1)

            # Display all players' choices if not already shown
            if not group.remaining_images_displayed:
                group.remaining_images_displayed = True
                
                # Get computer player choices from storage
                computer_players = json.loads(group.computer_player_choices)
                
                # Create a map of all players' chosen images
                all_images = {}
                for virtual_id, virtual_data in computer_players.items():
                    all_images[int(virtual_id)] = f'practice_task/{virtual_data["chosen_image_computer"]}'
                    
                response[player.id_in_group] = {
                    **response.get(player.id_in_group, {}),
                    'display_all_images': True,
                    'all_images': all_images,
                    'start_display_timer': True
                }
                    
                player.participant.vars['display_phase_end_time'] = time.time() + 4
                return response

            return response

        # ---- SECOND CHOICE PHASE ----
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
            # Process computer choice if real player didn't respond
            if not player.field_maybe_none('choice2'):
                player.computer_choice2 = random.choice(['left', 'right'])
                player.choice2 = player.computer_choice2
                player.chosen_image_two = player.left_image if player.computer_choice2 == 'left' else player.right_image
                
                # Use transparent images for computer choices
                if player.chosen_image_two == 'option1A.bmp':
                    player.chosen_image_computer_two = 'option1A.bmp'
                else:
                    player.chosen_image_computer_two = 'option1B.bmp'
            
            # Calculate metrics for choice
            if player.field_maybe_none('chosen_image_two') is not None:
                player.chosen_image_two_binary = 1 if player.chosen_image_two == 'option1A.bmp' else 2
            else:
                print(f"Warning: chosen_image_two is None for player {player.id_in_group}")

            # Move to second betting phase if not already there
            if not group.bet_container_displayed:
                group.bet_container_displayed = True
                return {player.id_in_group: dict(
                    second_choice_timer_ended=True,
                    show_bet_container=True, 
                    start_second_bet_timer=True, 
                    highlight_selected_image=player.chosen_image_two,
                    computer_second_choice=player.computer_choice2 if not player.field_maybe_none('choice2') else player.choice2
                )}

        # ---- SECOND BET PHASE ----
        if 'second_bet' in data:
            player.bet2 = int(data['second_bet'])
            player.computer_bet_two = False
            player.second_bet_time = round(data['second_bet_time'] / 1000, 2)

        # Handle second bet timer expiration and round completion
        if 'second_bet_timer_ended' in data:
            if not group.second_bet_timer_ended_executed:
                group.second_bet_timer_ended_executed = True
                response = {}
                
                # Assign computer bet if needed
                if player.bet2 == 0:
                    random_bet = random.randint(1, 3)
                    player.bet2 = random_bet
                    player.computer_bet_two = True
                    player.second_bet_time = 6.0
                    response[player.id_in_group] = dict(highlight_computer_second_bet=player.bet2)

                # Calculate final results for the round
                group.set_round_reward()
                group.calculate_player_rewards()

                # Calculate earnings for real player
                player.choice2_earnings = player.bet2 * 20 * player.trial_reward if player.trial_reward == 1 else -1 * player.bet2 * 20
                player.choice2_sum_earnings = sum([prev_player.choice2_earnings for prev_player in player.in_previous_rounds()]) + player.choice2_earnings
                player.loss_or_gain = -1 if player.choice2_earnings < 0 else 1

                # Generate random delay before next round
                group.generate_intertrial_interval()
                group.next_round_transition_time = time.time() * 1000 + group.intertrial_interval

                # Prepare final display information
                # Calculate rewards for computer players and update their data
                computer_players = json.loads(group.computer_player_choices)
                for virtual_id, virtual_data in computer_players.items():
                    # Calculate reward directly based on chosen image
                    if virtual_data['chosen_image_two'] == 'option1A.bmp':
                        virtual_data['trial_reward'] = group.round_reward_A
                    else:
                        virtual_data['trial_reward'] = group.round_reward_B
                
                # Save updated computer players data
                group.computer_player_choices = json.dumps(computer_players)
                
                # Create dictionaries for chosen images and win/loss status
                chosen_images_secondchoicepage = {
                    player.id_in_group: f"practice_task/{player.chosen_image_computer_two if player.computer_choice_two else player.chosen_image_two}"
                }
                win_loss_images = {
                    player.id_in_group: f'practice_task/{"win" if player.trial_reward == 1 else "loss"}.png'
                }
                
                # Add computer players to the results
                for virtual_id, virtual_data in computer_players.items():
                    int_id = int(virtual_id)
                    chosen_images_secondchoicepage[int_id] = f"practice_task/{virtual_data['chosen_image_computer_two']}"
                    win_loss_images[int_id] = f'practice_task/{"win" if virtual_data["trial_reward"] == 1 else "loss"}.png'

                # Prepare final response
                response[player.id_in_group] = {
                    **response.get(player.id_in_group, {}),
                    **dict(
                        show_results=True,
                        second_bet_reward=player.choice2_earnings,
                        chosen_images=chosen_images_secondchoicepage,
                        win_loss_images=win_loss_images,
                        player_win_loss_image=win_loss_images[player.id_in_group],
                        intertrial_interval=group.intertrial_interval,
                        round_number=player.round_number,
                        num_rounds=C.NUM_ROUNDS,
                        selected_bet=player.bet2,
                        second_choice=player.choice2
                    )
                }
                
                return response

        # Default response - echo back any unhandled data
        return {player.id_in_group: data}

    @staticmethod
    def display_remaining_images(player, players):
        """
        Helper method to prepare the display of other players' choices
        Creates a response showing what images each player chose
        NOTE: This method is no longer used in single-player mode
        but kept for compatibility
        """
        import json
        
        group = player.group
        computer_players = {}
        
        if group.field_maybe_none('computer_player_choices'):
            computer_players = json.loads(group.computer_player_choices)
        
        all_images = {}
        for virtual_id, virtual_data in computer_players.items():
            all_images[int(virtual_id)] = f'practice_task/{virtual_data["chosen_image_computer"]}'
        
        return {player.id_in_group: dict(
            display_all_images=True,
            all_images=all_images
        )}

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

page_sequence = [GroupingWaitPage, TransitionToPracticeTask, MyPage, FinalResults, MainTaskInstructions]

# -------------------------------------------------------------------------------------------------------------------- #