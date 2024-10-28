import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from websocket_utils import safe_websocket # Uncomment to enable safe websocket
from otree.api import *
from . import *
import random
import time
import csv

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
    # Set a fixed random seed to ensure the same sequence every time
    # Or you can remove this line to generate a new sequence each time
    random.seed(49)  # You can change this number, but keep it constant

    sequence = []
    current_image = random.choice(['option1A.bmp', 'option1B.bmp'])
    reversal_rounds = []
    
    # Generate reversal rounds
    current_round = random.randint(8, 12)
    while current_round <= NUM_ROUNDS:
        reversal_rounds.append(current_round)
        current_round += random.randint(8, 12)

    for round_number in range(1, NUM_ROUNDS + 1):
        if round_number in reversal_rounds:
            current_image = 'option1B.bmp' if current_image == 'option1A.bmp' else 'option1A.bmp'
        sequence.append((round_number, current_image))

    # Save sequence to CSV
    file_path = os.path.join(os.getcwd(), 'reversal_sequence.csv')
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['round', 'seventy_percent_image'])
        writer.writerows(sequence)

    print(f"Reversal rounds: {reversal_rounds}")
    return sequence, reversal_rounds

# -------------------------------------------------------------------------------------------------------------------- #
# Generate a reward sequence for the experiment based on the number of rounds and reversal rounds
# The sequence is generated randomly with reversal rounds every 8-12 rounds, but remains the same for all groups

# Define constants at the top level
NUM_ROUNDS = 60
REWARD_PROBABILITY_A = 0.7
REWARD_PROBABILITY_B = 0.3

def generate_reward_sequence(num_rounds, reversal_rounds):
    sequence = []
    current_high_prob_image = 'A'
    high_prob_rewards = 0
    low_prob_rewards = 0
    target_high_rewards = 42
    target_low_rewards = 18

    csv_data = [['Round', 'High Prob', 'reward_A', 'reward_B']]

    print("\nGenerated Reward Sequence:")
    print("Round | High Prob | reward_A | reward_B")
    print("------|-----------|----------|----------")

    def can_add_high_prob():
        if len(sequence) < 3:
            return True
        return not all(s[0] if current_high_prob_image == 'A' else s[1] for s in sequence[-3:])

    def can_add_low_prob():
        if len(sequence) < 3:
            return True
        return not all(s[1] if current_high_prob_image == 'A' else s[0] for s in sequence[-3:])

    for round_num in range(1, num_rounds + 1):
        if round_num in reversal_rounds:
            current_high_prob_image = 'B' if current_high_prob_image == 'A' else 'A'
            print("-------|-----------|----------|----------")
            csv_data.append(['-------|-----------|----------|----------'])

        remaining_rounds = num_rounds - round_num + 1
        min_high_needed = target_high_rewards - high_prob_rewards
        min_low_needed = target_low_rewards - low_prob_rewards

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

        if choice == 'high' and can_add_high_prob():
            reward_A, reward_B = (1, 0) if current_high_prob_image == 'A' else (0, 1)
            high_prob_rewards += 1
        else:
            reward_A, reward_B = (0, 1) if current_high_prob_image == 'A' else (1, 0)
            low_prob_rewards += 1

        sequence.append((reward_A, reward_B))
        print(f"{round_num:5d} | {current_high_prob_image:9s} | {reward_A:8d} | {reward_B:8d}")
        csv_data.append([round_num, current_high_prob_image, reward_A, reward_B])

    high_prob_percentage = (high_prob_rewards / num_rounds) * 100
    low_prob_percentage = (low_prob_rewards / num_rounds) * 100
    
    print("\nReward Statistics:")
    print(f"High probability rewards: {high_prob_rewards}/{num_rounds} ({high_prob_percentage:.2f}%)")
    print(f"Low probability rewards: {low_prob_rewards}/{num_rounds} ({low_prob_percentage:.2f}%)")

    # Save to CSV
    with open('reward_sequence.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_data)

    print("Reward sequence saved to 'reward_sequence.csv'")

    return sequence

# Generate the sequences once when the module is imported
TRIAL_SEQUENCE, REVERSAL_ROUNDS = generate_trial_sequence()
REWARD_SEQUENCE = generate_reward_sequence(60, REVERSAL_ROUNDS)

# -------------------------------------------------------------------------------------------------------------------- #
# Base Constants: Used to define constants across all pages and subsessions in the game

class C(BaseConstants):
    NAME_IN_URL = 'main_task'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = NUM_ROUNDS
    REWARD_PROBABILITY_A = REWARD_PROBABILITY_A
    REWARD_PROBABILITY_B = REWARD_PROBABILITY_B
    IMAGES = ['option1A.bmp', 'option1B.bmp']
    AVATAR_IMAGE = 'main_task/avatar_male.png'
    IMAGE_PATHS = {
        'option1A.bmp': '_static/main_task/option1A.bmp',
        'option1B.bmp': '_static/main_task/option1B.bmp',
        'option1A_tr.bmp': '_static/main_task/option1A_tr.bmp',
        'option1B_tr.bmp': '_static/main_task/option1B_tr.bmp',
        'avatar_male.png': '_static/main_task/avatar_male.png',
    }
    REWARD_SEQUENCE = REWARD_SEQUENCE

# -------------------------------------------------------------------------------------------------------------------- #
# Generate a sequence of earnings types for the experiment based on the number of rounds
# The sequence is generated randomly with alternating choice1_earnings and choice2_earnings

def generate_earnings_sequence(num_rounds):
    random.seed(42)  # Ensure reproducibility
    sequence = ['choice1_earnings' if i % 2 == 0 else 'choice2_earnings' for i in range(num_rounds)]
    random.shuffle(sequence)
    
    for i, earnings_type in enumerate(sequence, 1):
        pass # print(f"Round {i}: {earnings_type}") # Uncomment to print the sequence of earnings types
    
    return sequence

EARNINGS_SEQUENCE = generate_earnings_sequence(NUM_ROUNDS)

# -------------------------------------------------------------------------------------------------------------------- #
# ---- SUBSESSIONS: USED TO DEFINE THE ROUNDS FOR REVERSAL AND BOTS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class Subsession(BaseSubsession):

    def creating_session(self):
        if self.round_number > 1:
            for group in self.get_groups():
                group.round_reward_set = False

# Define the sequence of rounds for the experiment based on the trial sequence generated earlier
# The sequence is the same for all groups and is used to determine the reward probabilities for each round

    def get_reversal_rounds(self):
        return [round for round in REVERSAL_ROUNDS if round <= self.round_number]

    def collect_bot_data(self):
        data = []
        for p in self.get_players():
            player_data = {
                'round_number': self.round_number,
                'player_id': p.id_in_group,
                'choice1': p.choice1,
                'bet1': p.bet1,
                'choice2': p.choice2,
                'bet2': p.bet2,
                'trial_reward': p.trial_reward,
                'choice2_earnings': p.choice2_earnings
            }
            data.append(player_data)
        return data

# -------------------------------------------------------------------------------------------------------------------- #
# ---- GROUP-LEVEL VARIABLES: USED TO TRACK ROUND REWARDS, REWARD PROBABILITIES AND INTERTRIAL INTERVALS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class Group(BaseGroup):
    current_round = models.IntegerField(initial=1)
    my_page_load_time = models.FloatField()
    round_reward_A = models.IntegerField()
    round_reward_B = models.IntegerField()  
    intertrial_interval = models.IntegerField(initial=0)
    second_bet_timer_ended_executed = models.BooleanField(initial=False)
    next_round_transition_time = models.FloatField()
    reward_probability_A = models.FloatField(initial=0.7)
    reward_probability_B = models.FloatField(initial=0.3)
    seventy_percent_image = models.StringField(initial='option1A.bmp')
    thirty_percent_image = models.StringField(initial='option1B.bmp')
    reversal_rounds = models.StringField(initial='')
    bet_container_displayed = models.BooleanField(initial=False)
    remaining_images_displayed = models.BooleanField(initial=False)
    reversal_happened = models.BooleanField(initial=False)
    round_reward_set = models.BooleanField(initial=False)
    all_players_loaded = models.BooleanField(initial=False)
    players_loaded_count = models.IntegerField(initial=0)

#### ---------------- Define the round reward ------------------------ ####
# The round reward is randomly generated based on the reward probabilities for each image

    def set_round_reward(self):
        if not self.round_reward_set:
            self.round_reward_A, self.round_reward_B = C.REWARD_SEQUENCE[self.round_number - 1]
            self.round_reward_set = True
            print(f"Round {self.round_number}: reward_A = {self.round_reward_A}, reward_B = {self.round_reward_B}")

    def calculate_player_rewards(self):
        for p in self.get_players():
            if p.field_maybe_none('chosen_image_two') is None:
                continue  # Skip players who haven't made a choice yet

            if p.chosen_image_two == self.seventy_percent_image:
                potential_reward = self.round_reward_A if self.seventy_percent_image == 'option1A.bmp' else self.round_reward_B
            else:
                potential_reward = self.round_reward_B if self.seventy_percent_image == 'option1A.bmp' else self.round_reward_A

            p.trial_reward = potential_reward

#### ---------------- Define payoffs ------------------------ ####
# The payoff for each round is calculated as: payoff = bet * 20 * reward

    def set_payoffs(self):
        self.set_round_reward()
        self.calculate_player_rewards()

        print(f"\n--- Round {self.round_number} Results ---")

        for p in self.get_players():
            # Calculate choice2_earnings (based on second choice and bet)
            p.choice2_earnings = p.bet2 * 20 * p.trial_reward if p.trial_reward == 1 else -1 * p.bet2 * 20
            
            # Calculate choice1_earnings (based on first choice and bet)
            choice1_reward = 0
            if p.chosen_image_one == 'option1A.bmp':
                choice1_reward = self.round_reward_A
            elif p.chosen_image_one == 'option1B.bmp':
                choice1_reward = self.round_reward_B
            
            p.choice1_earnings = p.bet1 * 20 * choice1_reward if choice1_reward == 1 else -1 * p.bet1 * 20

    print("-----------------------------\n")

#### --------------- Define the intertrial interval ------------------------ ####
# The intertrial interval is randomly generated between 3000ms and 4000ms

    def generate_intertrial_interval(self):
        self.intertrial_interval = random.randint(3000, 4000)
        print(f"Intertrial interval of {self.intertrial_interval}ms generated")

#### ----------- Define and record the reversal learning rounds ------------------- ####
# Reversals are triggered every 8-12 rounds and the reward probabilities are switched

    def reversal_learning(self):
        current_round_data = next((item for item in TRIAL_SEQUENCE if item[0] == self.round_number), None)
        
        if current_round_data:
            self.seventy_percent_image = current_round_data[1]
            self.thirty_percent_image = 'option1B.bmp' if self.seventy_percent_image == 'option1A.bmp' else 'option1A.bmp'
            previous_round = self.in_round(self.round_number - 1) if self.round_number > 1 else None

            if self.round_number in REVERSAL_ROUNDS:
                self.reversal_happened = True
            else:
                self.reversal_happened = False

            if self.seventy_percent_image == 'option1A.bmp':
                self.reward_probability_A = 0.7
                self.reward_probability_B = 0.3
            else:
                self.reward_probability_A = 0.3
                self.reward_probability_B = 0.7

        print(f"Round {self.round_number}: 70% image is {self.seventy_percent_image}, 30% image is {self.thirty_percent_image}")
        print(f"Current probabilities: option1A.bmp - {self.reward_probability_A}, option1B.bmp - {self.reward_probability_B}")

#### ------------- Define the reset fields method ------------------- ####
# This method is used to reset the group-level variables at the start of each round

    def reset_fields(self):
        self.current_round = 1
        self.my_page_load_time = None
        self.round_reward_A = 0
        self.round_reward_B = 0
        self.intertrial_interval = 0
        self.second_bet_timer_ended_executed = False
        self.next_round_transition_time = None
        self.reversal_happened = False

# -------------------------------------------------------------------------------------------------------------------- #
# ---- PLAYER-LEVEL VARIABLES: USED TO TRACK CHOICES, BETS, EARNINGS AND A WHOLE LOT ELSE ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# The Player class is used to define the variables that are stored at the player level
# The variables include choices, bets, rewards, and timings for each player

class Player(BasePlayer):
    choice1 = models.StringField(initial='')
    choice2 = models.StringField(initial='')
    computer_choice1 = models.StringField(initial='')
    computer_choice2 = models.StringField(initial='')
    bet1 = models.IntegerField(initial=0)
    bet2 = models.IntegerField(initial=0)
    left_image = models.StringField()
    right_image = models.StringField()
    trial_reward = models.IntegerField(initial=0)
    chosen_image_one = models.StringField()
    chosen_image_one_binary = models.IntegerField()
    chosen_image_two = models.StringField(initial=None)
    chosen_image_two_binary = models.IntegerField()
    choice1_with = models.IntegerField(initial=0)
    choice1_against = models.IntegerField(initial=0)
    choice2_with = models.IntegerField(initial=0)
    choice2_against = models.IntegerField(initial=0)
    chosen_image_computer = models.StringField(initial='')
    chosen_image_computer_two = models.StringField(initial='')
    choice1_accuracy = models.BooleanField()
    choice2_accuracy = models.BooleanField()
    switch_vs_stay = models.IntegerField()
    my_page_load_time = models.FloatField()
    individual_page_load_time = models.FloatField()
    initial_choice_time = models.FloatField()
    initial_bet_time = models.FloatField()
    second_choice_time = models.FloatField()
    second_bet_time = models.FloatField()
    choice1_earnings = models.IntegerField(initial=0)
    choice2_earnings = models.IntegerField(initial=0)
    choice1_sum_earnings = models.IntegerField(initial=0)
    choice2_sum_earnings = models.IntegerField(initial=0)
    bonus_payment_score = models.IntegerField(initial=0)
    base_payoff = models.CurrencyField(initial=6)
    bonus_payoff = models.CurrencyField(initial=0)
    total_payoff = models.CurrencyField(initial=0)
    loss_or_gain = models.IntegerField()
    computer_choice_one = models.BooleanField(initial=True)
    computer_bet_one = models.BooleanField(initial=False)
    computer_choice_two = models.BooleanField(initial=True)
    computer_bet_two = models.BooleanField(initial=False)
    player_1_choice_one = models.IntegerField()
    player_2_choice_one = models.IntegerField()
    player_3_choice_one = models.IntegerField()
    player_4_choice_one = models.IntegerField()
    player_1_choice_two = models.IntegerField()
    player_2_choice_two = models.IntegerField()
    player_3_choice_two = models.IntegerField()
    player_4_choice_two = models.IntegerField()
    player_1_computer_choice_one = models.BooleanField()
    player_2_computer_choice_one = models.BooleanField()
    player_3_computer_choice_one = models.BooleanField()
    player_4_computer_choice_one = models.BooleanField()
    player_1_computer_choice_two = models.BooleanField()
    player_2_computer_choice_two = models.BooleanField()
    player_3_computer_choice_two = models.BooleanField()
    player_4_computer_choice_two = models.BooleanField()
    player1_choice1_accuracy = models.BooleanField()
    player2_choice1_accuracy = models.BooleanField()
    player3_choice1_accuracy = models.BooleanField()
    player4_choice1_accuracy = models.BooleanField()
    player1_choice2_accuracy = models.BooleanField()
    player2_choice2_accuracy = models.BooleanField()
    player3_choice2_accuracy = models.BooleanField()
    player4_choice2_accuracy = models.BooleanField()
    loss_or_gain_player1 = models.IntegerField()
    loss_or_gain_player2 = models.IntegerField()
    loss_or_gain_player3 = models.IntegerField()
    loss_or_gain_player4 = models.IntegerField()
    manual_second_choice = models.BooleanField(initial=False)

# Reset the player-level variables at the start of each round 

    def reset_fields(self):
        self.choice1 = ''
        self.bet1 = 0
        self.trial_reward = 0
        self.chosen_image_one = ''
        self.chosen_image_one_binary = None
        self.chosen_image_two = None
        self.chosen_image_two_binary = None
        self.choice1_with = 0
        self.choice1_against = 0
        self.choice2_with = 0
        self.choice2_against = 0
        self.chosen_image_computer = ''
        self.chosen_image_computer_two = ''
        self.choice1_accuracy = None
        self.choice2_accuracy = None
        self.switch_vs_stay = None
        self.my_page_load_time = None
        self.initial_choice_time = None
        self.initial_bet_time = None
        self.second_choice_time = None
        self.second_bet_time = None
        self.computer_choice_one = True
        self.computer_bet_one = False
        self.computer_choice_two = True
        self.computer_bet_two = False
        self.player_1_choice_one = None
        self.player_1_choice_two = None
        self.player_2_choice_one = None
        self.player_2_choice_two = None
        self.player_1_computer_choice_one = None
        self.player_1_computer_choice_two = None
        self.player_2_computer_choice_one = None
        self.player_2_computer_choice_two = None
        self.player1_choice1_accuracy = None 
        self.player1_choice2_accuracy = None
        self.player2_choice1_accuracy = None
        self.player2_choice2_accuracy = None
        self.loss_or_gain = None
        self.loss_or_gain_player1 = None
        self.loss_or_gain_player2 = None
        self.player_3_choice_one = None
        self.player_3_choice_two = None
        self.player_4_choice_one = None
        self.player_4_choice_two = None
        self.player_3_computer_choice_one = None
        self.player_3_computer_choice_two = None
        self.player_4_computer_choice_one = None
        self.player_4_computer_choice_two = None
        self.player3_choice1_accuracy = None
        self.player3_choice2_accuracy = None
        self.player4_choice1_accuracy = None
        self.player4_choice2_accuracy = None
        self.loss_or_gain_player3 = None
        self.loss_or_gain_player4 = None

# Calculate the number of players who made the same choice as the current player
# This is used to calculate the social influence effect

    def calculate_choice_comparisons(self):
        other_players = self.get_others_in_group()
        
        # For choice1
        self.choice1_with = sum(1 for p in other_players if p.chosen_image_one == self.chosen_image_one)
        self.choice1_against = len(other_players) - self.choice1_with
        
        # For choice2
        self.choice2_with = sum(1 for p in other_players if p.chosen_image_two == self.chosen_image_two)
        self.choice2_against = len(other_players) - self.choice2_with

# Calculate the payoffs for each player based on their choices and rewards
# The payoff is calculated as: payoff = £6 + (reward_earnings / 75)

    def calculate_payoffs(self):
        self.base_payoff = cu(6)  # Base payoff of £6
        
        if self.bonus_payment_score <= 0:
            self.bonus_payoff = cu(0)
        else:
            self.bonus_payoff = cu(round(self.bonus_payment_score / 750, 2))
        
        self.total_payoff = self.base_payoff + self.bonus_payoff

    def calculate_choice1_earnings(self):
        if self.chosen_image_one == 'option1A.bmp':
            choice1_reward = self.group.round_reward_A
        elif self.chosen_image_one == 'option1B.bmp':
            choice1_reward = self.group.round_reward_B
        else:
            pass
            return

        self.choice1_earnings = self.bet1 * 20 * choice1_reward if choice1_reward == 1 else -1 * self.bet1 * 20

# -------------------------------------------------------------------------------------------------------------------- #
# ---- MYPAGE: WHERE PLAYERS MAKE THEIR FIRST CHOICE, FIRST BET AND PREFERENCE CHOICES ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class MyPage(Page):
    form_model = 'player'
    form_fields = ['choice1', 'bet1', 'choice2', 'bet2']

    @staticmethod
    def js_vars(player: Player):
        return dict(
            page_start_time=int(time.time() * 1000)
        )

    @staticmethod
    def get_timeout_seconds(player: Player):
        return 4200

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.participant.vars['timed_out'] = True

        # Handle both first and second choices/bets
        for choice_field, computer_choice_field, bet_field, image_field in [
            ('choice1', 'computer_choice1', 'bet1', 'chosen_image_one'),
            ('choice2', 'computer_choice2', 'bet2', 'chosen_image_two')
        ]:
            manual_choice = player.field_maybe_none(choice_field)
            computer_choice = player.field_maybe_none(computer_choice_field)

            # Specific condition to keep manual choice if computer choice is not 'left' or 'right'
            if manual_choice is not None and (computer_choice is None or computer_choice not in ['left', 'right']):
                # Keep the manual choice, do nothing
                pass
            elif computer_choice in ['left', 'right']:
                # If there's a valid computer choice, use it and clear the manual choice
                setattr(player, choice_field, None)
                setattr(player, computer_choice_field, computer_choice)
            elif manual_choice is None and computer_choice is None:
                # If both are None, ensure both fields are explicitly set to None
                setattr(player, choice_field, None)
                setattr(player, computer_choice_field, None)

            # Determine the final choice for setting the chosen image
            final_choice = getattr(player, computer_choice_field) or getattr(player, choice_field)

            # Set the chosen image field based on the final choice
            if final_choice in ['left', 'right']:
                chosen_image = player.left_image if final_choice == 'left' else player.right_image
                setattr(player, image_field, chosen_image)
                player.participant.vars[image_field] = chosen_image
            else:
                setattr(player, image_field, None)
                player.participant.vars[image_field] = None

            # Handle bets
            bet_value = player.field_maybe_none(bet_field)
            if bet_value is None:
                setattr(player, bet_field, 1)  # Default to 1 if no bet was made

        # The rest of the method remains the same
        # Calculate earnings
        player.calculate_choice1_earnings()
        player.choice2_earnings = player.bet2 * 20 * player.trial_reward if player.trial_reward == 1 else -1 * player.bet2 * 20

        # Calculate and update bonus_payment_score
        earnings_type = EARNINGS_SEQUENCE[player.round_number - 1]
        current_round_earnings = player.choice1_earnings if earnings_type == 'choice1_earnings' else player.choice2_earnings

        if player.round_number == 1:
            player.bonus_payment_score = current_round_earnings
            player.choice1_sum_earnings = player.choice1_earnings
            player.choice2_sum_earnings = player.choice2_earnings
        else:
            previous_player = player.in_round(player.round_number - 1)
            player.bonus_payment_score = previous_player.bonus_payment_score + current_round_earnings
            player.choice1_sum_earnings = previous_player.choice1_sum_earnings + player.choice1_earnings
            player.choice2_sum_earnings = previous_player.choice2_sum_earnings + player.choice2_earnings

        # Calculate choice comparisons and accuracies
        player.calculate_choice_comparisons()
        player.choice1_accuracy = player.chosen_image_one == player.group.seventy_percent_image
        player.choice2_accuracy = player.chosen_image_two == player.group.seventy_percent_image
        player.switch_vs_stay = 1 if player.chosen_image_one != player.chosen_image_two else 0

    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        if player.participant.vars.get('timed_out', False):
            return 'player_left'

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        if group.round_number > 1:
            group.reset_fields()
            for p in group.get_players():
                p.reset_fields()

        images = C.IMAGES.copy()
        random.shuffle(images)
        left_image = images[0]
        right_image = images[1]
        player.left_image = left_image
        player.right_image = right_image
        other_players = player.get_others_in_group()

        return {
            'left_image': f'main_task/{left_image}',
            'right_image': f'main_task/{right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': [p.id_in_group for p in other_players],
            'chosen_images': {p.id_in_group: f"main_task/{p.field_maybe_none('chosen_image_computer') or p.field_maybe_none('chosen_image_one') or 'default_image.png'}" for p in group.get_players()},
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
    @safe_websocket(max_retries=5, retry_delay=0.2) # Uncomment to enable safe websocket
    def live_method(player, data):
        # print(f"Received data: {data}") # Uncomment to print received data
        group = player.group
        players = group.get_players()
        response = {}

        if 'my_page_load_time' in data:
            # Record individual player's load time
            player.my_page_load_time = round(data['my_page_load_time'] / 1000, 2)
            player.individual_page_load_time = round(data['individual_page_load_time'] / 1000, 2)
            
            # Increment the counter for loaded players if not already counted
            if not player.field_maybe_none('my_page_load_time'):
                group.players_loaded_count += 1
            
            # Only proceed when all players have loaded
            if group.players_loaded_count == C.PLAYERS_PER_GROUP and not group.all_players_loaded:
                group.all_players_loaded = True
                group.my_page_load_time = round(max(p.my_page_load_time for p in players), 2)
                group.set_round_reward()
                group.reversal_learning()
                return {p.id_in_group: dict(start_choice_phase_timer=True) for p in players}
                
            return {player.id_in_group: dict(acknowledged=True)}

        if 'initial_choice_time' in data:
            if data['initial_choice_time'] is not None:
                actual_choice_time = round((data['initial_choice_time'] - player.individual_page_load_time) / 1000, 2)
                player.initial_choice_time = min(actual_choice_time, 3.0)
            else:
                player.initial_choice_time = 3.0

            if 'choice' in data and not player.field_maybe_none('chosen_image_one'):
                player.choice1 = data['choice']
                player.chosen_image_one = player.left_image if data['choice'] == 'left' else player.right_image
                player.participant.vars['chosen_image_one'] = player.chosen_image_one
                player.computer_choice_one = False

        if 'choice_phase_timer_ended' in data:
            for p in players:
                if p.field_maybe_none('choice1') is None or p.choice1 == '':
                    random_choice = random.choice(['left', 'right'])
                    p.choice1 = random_choice
                    p.computer_choice1 = random_choice  # Store the computer-made choice
                    p.chosen_image_one = p.left_image if random_choice == 'left' else p.right_image
                    p.participant.vars['chosen_image_one'] = p.chosen_image_one
                    p.initial_choice_time = 3.0
                    p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 2
                    p.computer_choice_one = True
                    if p.chosen_image_one == 'option1A.bmp':
                        p.chosen_image_computer = 'option1A_tr.bmp'
                    elif p.chosen_image_one == 'option1B.bmp':
                        p.chosen_image_computer = 'option1B_tr.bmp'
                    p.choice1_accuracy = p.chosen_image_one == group.seventy_percent_image
                else:
                    p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 2
                    p.choice1_accuracy = p.chosen_image_one == group.seventy_percent_image

            for p in players:
                other_players = p.get_others_in_group()
                p.player_1_choice_one = other_players[0].chosen_image_one_binary
                p.player_2_choice_one = other_players[1].chosen_image_one_binary
                p.player_3_choice_one = other_players[2].chosen_image_one_binary
                p.player_4_choice_one = other_players[3].chosen_image_one_binary
                p.player_1_computer_choice_one = other_players[0].computer_choice_one
                p.player_2_computer_choice_one = other_players[1].computer_choice_one
                p.player_3_computer_choice_one = other_players[2].computer_choice_one
                p.player_4_computer_choice_one = other_players[3].computer_choice_one
                p.player1_choice1_accuracy = other_players[0].choice1_accuracy
                p.player2_choice1_accuracy = other_players[1].choice1_accuracy
                p.player3_choice1_accuracy = other_players[2].choice1_accuracy
                p.player4_choice1_accuracy = other_players[3].choice1_accuracy

            return {p.id_in_group: dict(show_bet_container=True, start_bet_timer=True, highlight_selected_choice=p.choice1) for p in players}

        if 'show_bet_container' in data and data['show_bet_container']:
            for p in players:
                p.calculate_choice_comparisons()

            player.participant.vars['bet_timer_started'] = True
            player.participant.vars['bet_phase_start_time'] = time.time()
            return {player.id_in_group: dict(start_bet_timer=True)}

        if 'bet' in data:
            # Only process the manual bet if a computer bet hasn't been made yet
            if not player.computer_bet_one:  # Add this condition
                player.bet1 = int(data['bet'])
                player.participant.vars['bet1'] = player.bet1
                player.initial_bet_time = round(data['initial_bet_time'] / 1000, 2)
                player.computer_bet_one = False

        if 'bet_timer_ended' in data:
            response = {}
            for p in players:
                # Only assign computer bet if no bet has been made yet
                if not p.field_maybe_none('bet1') and not p.computer_bet_one:  # Modified condition
                    random_bet = random.randint(1, 3)
                    p.bet1 = random_bet
                    p.participant.vars['bet1'] = p.bet1
                    p.initial_bet_time = 3.0
                    p.computer_bet_one = True
                    response[p.id_in_group] = dict(highlight_computer_bet=p.bet1)

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

        # Second choice phase
        if 'second_choice' in data and data.get('manual_second_choice', False):
            print(f"Received manual second choice for player {player.id_in_group}")
            
            player.choice2 = data['second_choice']
            player.chosen_image_two = player.left_image if data['second_choice'] == 'left' else player.right_image
            player.participant.vars['chosen_image_two'] = player.chosen_image_two
            player.computer_choice_two = False
            player.manual_second_choice = True
            player.second_choice_time = round(data['second_choice_time'] / 1000, 2)
            player.chosen_image_two_binary = 1 if player.chosen_image_two == 'option1A.bmp' else 2
            player.choice2_accuracy = player.chosen_image_two == player.group.seventy_percent_image
            player.switch_vs_stay = 1 if player.field_maybe_none('chosen_image_one') != player.chosen_image_two else 0
            player.chosen_image_computer_two = ''
            player.computer_choice2 = ''
            
            return {player.id_in_group: dict(highlight_selected_second_choice=player.choice2)}

        if 'second_choice_timer_ended' in data:
            for p in players:
                if not p.field_maybe_none('choice2'):  # If no manual choice was made
                    p.computer_choice2 = random.choice(['left', 'right'])
                    p.choice2 = p.computer_choice2
                    p.chosen_image_two = p.left_image if p.computer_choice2 == 'left' else p.right_image
                    
                    if p.chosen_image_two == 'option1A.bmp':
                        p.chosen_image_computer_two = 'option1A_tr.bmp'
                    else:
                        p.chosen_image_computer_two = 'option1B_tr.bmp'
                
                # These calculations are done for both manual and computer choices
                if p.field_maybe_none('chosen_image_two') is not None:
                    p.chosen_image_two_binary = 1 if p.chosen_image_two == 'option1A.bmp' else 2
                    p.choice2_accuracy = p.chosen_image_two == p.group.seventy_percent_image
                    p.switch_vs_stay = 1 if p.field_maybe_none('chosen_image_one') != p.chosen_image_two else 0
                else:
                    print(f"Warning: chosen_image_two is None for player {p.id_in_group}")

            for p in players:
                other_players = p.get_others_in_group()
                p.player_1_choice_two = other_players[0].chosen_image_two_binary
                p.player_2_choice_two = other_players[1].chosen_image_two_binary
                p.player_3_choice_two = other_players[2].chosen_image_two_binary
                p.player_4_choice_two = other_players[3].chosen_image_two_binary
                p.player_1_computer_choice_two = other_players[0].computer_choice_two
                p.player_2_computer_choice_two = other_players[1].computer_choice_two
                p.player_3_computer_choice_two = other_players[2].computer_choice_two
                p.player_4_computer_choice_two = other_players[3].computer_choice_two
                p.player1_choice2_accuracy = other_players[0].choice2_accuracy
                p.player2_choice2_accuracy = other_players[1].choice2_accuracy
                p.player3_choice2_accuracy = other_players[2].choice2_accuracy
                p.player4_choice2_accuracy = other_players[3].choice2_accuracy

            # Calculate comparisons for the second choice
            for p in players:
                p.calculate_choice_comparisons()

            if not group.bet_container_displayed:
                group.bet_container_displayed = True
                return {p.id_in_group: dict(
                    second_choice_timer_ended=True,
                    show_bet_container=True, 
                    start_second_bet_timer=True, 
                    highlight_selected_image=p.chosen_image_two,
                    computer_second_choice=p.computer_choice2 if not p.field_maybe_none('choice2') else p.choice2
                ) for p in players}
    
        # Second bet phase
        if 'second_bet' in data:
            player.bet2 = int(data['second_bet'])
            player.bet2 = player.bet2
            player.computer_bet_two = False
            player.second_bet_time = round(data['second_bet_time'] / 1000, 2)

        if 'second_bet_timer_ended' in data:
            if not group.second_bet_timer_ended_executed:
                group.second_bet_timer_ended_executed = True
                response = {}

                for p in players:
                    if p.bet2 == 0:
                        random_bet = random.randint(1, 3)
                        p.bet2 = random_bet
                        p.bet2 = p.bet2
                        p.computer_bet_two = True
                        p.second_bet_time = 3.0
                        response[p.id_in_group] = dict(highlight_computer_second_bet=p.bet2)

                # Calculate rewards and prepare results for all players
                group.set_round_reward()
                group.calculate_player_rewards()

                for p in players:
                    p.choice2_earnings = p.bet2 * 20 * p.trial_reward if p.trial_reward == 1 else -1 * p.bet2 * 20
                    p.choice2_sum_earnings = sum([prev_player.choice2_earnings for prev_player in p.in_previous_rounds()]) + p.choice2_earnings
                    p.loss_or_gain = -1 if p.choice2_earnings < 0 else 1

                for p in players:
                    other_players = p.get_others_in_group()
                    p.loss_or_gain_player1 = 0 if other_players[0].choice2_earnings < 0 else 1
                    p.loss_or_gain_player2 = 0 if other_players[1].choice2_earnings < 0 else 1
                    p.loss_or_gain_player3 = 0 if other_players[2].choice2_earnings < 0 else 1
                    p.loss_or_gain_player4 = 0 if other_players[3].choice2_earnings < 0 else 1

                group.generate_intertrial_interval()
                group.next_round_transition_time = time.time() * 1000 + group.intertrial_interval

                chosen_images_secondchoicepage = {
                    p.id_in_group: f"main_task/{p.chosen_image_computer_two if p.computer_choice_two else p.chosen_image_two}" 
                    for p in players
                }
                win_loss_images = {p.id_in_group: f'main_task/{"win" if p.trial_reward == 1 else "loss"}.png' for p in players}

                for p in players:
                    response[p.id_in_group] = {
                        **response.get(p.id_in_group, {}),
                        **dict(
                            show_results=True,
                            second_bet_reward=p.choice2_earnings,
                            chosen_images=chosen_images_secondchoicepage,
                            win_loss_images=win_loss_images,
                            player_win_loss_image=win_loss_images[p.id_in_group],
                            intertrial_interval=group.intertrial_interval,
                            round_number=player.round_number,
                            num_rounds=C.NUM_ROUNDS,
                            selected_bet=p.bet2,
                            second_choice=p.choice2
                        )
                    }

                return response

        return {p.id_in_group: data for p in group.get_players()}

    @staticmethod
    def display_remaining_images(player, players):
        response = {}
        for p in players:
            other_players = p.get_others_in_group()
            all_images = {}
            for op in other_players:
                chosen_image = op.chosen_image_computer if op.chosen_image_computer else op.chosen_image_one
                all_images[op.id_in_group] = f'main_task/{chosen_image}'
            response[p.id_in_group] = dict(
                display_all_images=True,
                all_images=all_images
            )
        
        return response

    @staticmethod
    def after_all_players_arrive(group: Group):
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
        player.calculate_payoffs()  # Calculate payoffs here

        # Calculate the final bonus_payment_score and choice1_sum_earnings
        final_bonus_score = player.in_round(C.NUM_ROUNDS).bonus_payment_score
        final_choice1_sum = player.in_round(C.NUM_ROUNDS).choice1_sum_earnings
        
        for round_num in range(1, C.NUM_ROUNDS + 1):
            round_score = player.in_round(round_num).bonus_payment_score
            round_choice1_sum = player.in_round(round_num).choice1_sum_earnings

        # Define column names
        column_names = [
            'Prolific ID',
            'Base Payoff',
            'Bonus Payoff',
            'Total Payoff',
            'Final Bonus Score',
            'Final Choice 1 Sum'
        ]

        # Prepare data row
        data = [
            player.participant.vars.get('prolific_id', 'Unknown'),
            float(player.base_payoff),
            float(player.bonus_payoff),
            float(player.total_payoff),
            final_bonus_score,
            final_choice1_sum
        ]
        
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.isfile('payoffs.csv')
        
        with open('payoffs.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                # Write column names if the file is being created for the first time
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

    @staticmethod
    def app_after_this_page(player, upcoming_apps):
        print('upcoming_apps is', upcoming_apps)
        return "submission"  # Hardcoded name of the last app

page_sequence = [MyPage, FinalResults]  

# -------------------------------------------------------------------------------------------------------------------- #