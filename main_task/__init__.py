from otree.live import live_payload_function
from otree.api import *
from . import *
import random
import time

author = 'Aamir Sohail'

doc = """
This is a multiplayer social influence task where players in groups of 5 make choices and bets to earn rewards in real time. 
The task is the same as reported in (Zhang & Glascher, 2020) https://www.science.org/doi/full/10.1126/sciadv.abb4159
"""

# -------------------------------------------------------------------------------------------------------------------- #
# ---- CONSTANTS: DEFINE CONSTANTS USED IN THE GAME INCLUDING NUMBER OF PLAYERS, ROUNDS AND REWARD PROBABILITIES------ #
# -------------------------------------------------------------------------------------------------------------------- #

class C(BaseConstants):
    NAME_IN_URL = 'main_task'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 3
    REWARD_PROBABILITY_A = 0.7
    REWARD_PROBABILITY_B = 0.3
    IMAGES = ['option1A.bmp', 'option1B.bmp']
    AVATAR_IMAGE = 'main_task/avatar_male.png'
    IMAGE_PATHS = {
        'option1A.bmp': '_static/main_task/option1A.bmp',
        'option1B.bmp': '_static/main_task/option1B.bmp',
        'option1A_tr.bmp': '_static/main_task/option1A_tr.bmp',
        'option1B_tr.bmp': '_static/main_task/option1B_tr.bmp',
        'avatar_male.png': '_static/main_task/avatar_male.png',
    }

# -------------------------------------------------------------------------------------------------------------------- #
# ---- SUBSESSIONS: USED TO DEFINE THE ROUNDS FOR REVERSAL AND BOTS ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class Subsession(BaseSubsession):
    reversal_rounds = models.StringField(initial='')

    def collect_bot_data(self):
        data = []
        for p in self.get_players():
            player_data = {
                'round_number': self.round_number,
                'player_id': p.id_in_group,
                'choice1': p.choice1,
                'bet1': p.bet1,
                'preference_choice': p.preference_choice,
                'preference_second_choice': p.preference_second_choice,
                'choice2': p.choice2,
                'bet2': p.bet2,
                'trial_reward': p.trial_reward,
                'trial_earnings': p.trial_earnings
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
    second_choice_timer_started = models.BooleanField(initial=False)
    all_players_made_choice2 = models.BooleanField(initial=False)
    all_manual_bet2 = models.BooleanField(initial=False)    
    all_players_preference_second_choice_time = models.FloatField()
    intertrial_interval = models.IntegerField(initial=0)
    manual_bets = models.BooleanField(initial=False)
    manual_preference_choices = models.BooleanField(initial=False)
    manual_second_preference_choices = models.BooleanField(initial=False)
    show_results_sent = models.BooleanField(initial=False)
    show_results_executed = models.BooleanField(initial=False)
    second_bet_timer_ended_executed = models.BooleanField(initial=False)
    next_round_transition_time = models.FloatField()
    reward_probability_A = models.FloatField(initial=0.7)
    reward_probability_B = models.FloatField(initial=0.3)
    seventy_percent_image = models.StringField(initial='option1A.bmp')
    reversal_rounds = models.StringField(initial='')
    redirect_triggered = models.BooleanField(initial=False)
    preference_choices_presented = models.BooleanField(initial=False)
    second_preference_choices_displayed = models.BooleanField(initial=False)
    bet_container_displayed = models.BooleanField(initial=False)
    remaining_images_displayed = models.BooleanField(initial=False)

    def set_round_reward(self):
        self.round_reward_A = 1 if random.random() < self.reward_probability_A else 0
        self.round_reward_B = 1 if random.random() < self.reward_probability_B else 0

#### ---------------- Define payoffs ------------------------ ####
# The payoff for each round is calculated as: payoff = bet * 20 * reward

    def set_payoffs(self):
        for p in self.get_players():
            if p.chosen_image_two == 'option1A.bmp':
                p.trial_reward = self.round_reward_A
            else:
                p.trial_reward = self.round_reward_B

            p.trial_earnings = p.bet2_computer * 20 * p.trial_reward
            p.total_reward_earnings += p.trial_earnings

#### --------------- Define the intertrial interval ------------------------ ####
# The intertrial interval is randomly generated between 2000ms and 4000ms

    def generate_intertrial_interval(self):
        self.intertrial_interval = random.randint(2000, 4000)
        print(f"Intertrial interval of {self.intertrial_interval}ms generated")

#### ----------- Define and record the reversal learning rounds ------------------- ####
# Reversals are randomly generated between 8 and 12 rounds

    def reversal_learning(self):
        if self.round_number == 1:
            reversal_rounds = []
            current_round = random.randint(8, 12)
            while current_round <= C.NUM_ROUNDS:
                reversal_rounds.append(current_round)
                current_round += random.randint(8, 12)
            self.session.vars['reversal_rounds'] = reversal_rounds

            # Randomly determine the initial image with 0.7 probability
            self.seventy_percent_image = random.choice(['option1A.bmp', 'option1B.bmp'])
            if self.seventy_percent_image == 'option1A.bmp':
                self.reward_probability_A = 0.7
                self.reward_probability_B = 0.3
            else:
                self.reward_probability_A = 0.3
                self.reward_probability_B = 0.7

            print(f"Reversal rounds generated: {reversal_rounds}")
            print(f"Initial 70% image: {self.seventy_percent_image}")
        else:
            reversal_rounds = self.session.vars.get('reversal_rounds', [])
            print(f"Reversal rounds for the game: {reversal_rounds}")

            previous_round = self.in_round(self.round_number - 1)
            self.seventy_percent_image = previous_round.seventy_percent_image
            self.reward_probability_A = previous_round.reward_probability_A
            self.reward_probability_B = previous_round.reward_probability_B

            if self.round_number in reversal_rounds:
                self.seventy_percent_image = 'option1B.bmp' if self.seventy_percent_image == 'option1A.bmp' else 'option1A.bmp'
                self.reward_probability_A, self.reward_probability_B = self.reward_probability_B, self.reward_probability_A
                print(f"Reversal occurred in round {self.round_number}")

        print(f"Current probabilities: option1A.bmp - {self.reward_probability_A}, option1B.bmp - {self.reward_probability_B}")
        print(f"Current 70% image: {self.seventy_percent_image}")

#### ------------- Define the reset fields method ------------------- ####
# This method is used to reset the group-level variables at the start of each round

    def reset_fields(self):
        self.current_round = 1
        self.my_page_load_time = None  # Changed to None
        self.round_reward_A = 0
        self.round_reward_B = 0
        self.second_choice_timer_started = False
        self.all_players_made_choice2 = False
        self.all_manual_bet2 = False
        self.intertrial_interval = 0
        self.manual_bets = False
        self.manual_preference_choices = False
        self.manual_second_preference_choices = False
        self.show_results_sent = False
        self.show_results_executed = False
        self.second_bet_timer_ended_executed = False
        self.next_round_transition_time = None  # Changed to None

# -------------------------------------------------------------------------------------------------------------------- #
# ---- PLAYER-LEVEL VARIABLES: USED TO TRACK CHOICES, BETS, EARNINGS AND A WHOLE LOT ELSE ------ #
# -------------------------------------------------------------------------------------------------------------------- #

# The Player class is used to define the variables that are stored at the player level
# The variables include choices, bets, rewards, and timings for each player

class Player(BasePlayer):
    choice1 = models.StringField(initial='')
    choice2 = models.StringField(initial='')
    choice2_computer = models.StringField(initial='')
    bet1 = models.IntegerField(initial=0)
    bet2 = models.IntegerField(initial=0)
    bet2_computer = models.IntegerField(initial=0)
    left_image = models.StringField()
    right_image = models.StringField()
    trial_reward = models.IntegerField(initial=0)
    chosen_image_one = models.StringField()
    chosen_image_one_binary = models.IntegerField()
    chosen_image_two = models.StringField()
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
    preference_choice = models.StringField(initial=0)
    preference_second_choice = models.StringField(initial=0)
    preference_choice_made = models.BooleanField(initial=False)
    preference_second_choice_made = models.BooleanField(initial=False)
    image_displayed = models.BooleanField(initial=False)
    second_image_displayed = models.BooleanField(initial=False)
    my_page_load_time = models.FloatField()
    initial_choice_time = models.FloatField()
    initial_bet_time = models.FloatField()
    preference_choice_time = models.FloatField()
    preference_second_choice_time = models.FloatField()
    second_choice_page_load_time = models.FloatField()
    second_choice_time = models.FloatField()
    second_bet_time = models.FloatField()
    trial_earnings = models.IntegerField(initial=0)
    total_reward_earnings = models.IntegerField(initial=0)
    loss_or_gain = models.IntegerField()
    computer_choice_one = models.BooleanField(initial=True)
    computer_bet_one = models.IntegerField(initial=1)
    computer_preference_choice_one = models.BooleanField(initial=True)
    button_pressed = models.BooleanField(initial=False)
    computer_preference_choice_two = models.BooleanField(initial=True)
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
    all_images_displayed = models.BooleanField(initial=False)

# Reset the player-level variables at the start of each round 

    def reset_fields(self):
        self.choice1 = ''
        # self.choice2 = ''
        self.bet1 = 0
        # self.bet2 = 0
        # self.left_image = ''  # Removed
        # self.right_image = ''  # Removed
        self.trial_reward = 0
        self.chosen_image_one = ''
        self.chosen_image_one_binary = None  # Changed to None
        self.chosen_image_two = None
        self.chosen_image_two_binary = None  # Changed to None
        self.choice1_with = 0
        self.choice1_against = 0
        self.choice2_with = 0
        self.choice2_against = 0
        self.chosen_image_computer = ''
        self.chosen_image_computer_two = ''
        self.choice1_accuracy = None  # Reset choice1_accuracy
        self.choice2_accuracy = None  # Reset choice2_accuracy
        self.switch_vs_stay = None  # Changed to None
        self.preference_choice = '0'
        self.preference_second_choice = '0'
        self.preference_choice_made = False
        self.preference_second_choice_made = False
        self.image_displayed = False
        self.second_image_displayed = False
        self.my_page_load_time = None  # Changed to None
        self.initial_choice_time = None  # Changed to None
        self.initial_bet_time = None  # Changed to None
        self.preference_choice_time = None  # Changed to None
        self.preference_second_choice_time = None  # Changed to None
        self.second_choice_page_load_time = None  # Changed to None
        self.second_choice_time = None  # Changed to None
        self.second_bet_time = None  # Changed to None
        # self.trial_earnings = 0
        self.computer_choice_one = True
        self.computer_bet_one = 1
        self.computer_preference_choice_one = True
        self.button_pressed = False
        self.computer_preference_choice_two = True
        self.computer_choice_two = True
        self.computer_bet_two = False
        self.player_1_choice_one = None  # Changed to None
        self.player_1_choice_two = None  # Changed to None
        self.player_2_choice_one = None  # Changed to None
        self.player_2_choice_two = None  # Changed to None
        self.player_1_computer_choice_one = None  # Changed to None
        self.player_1_computer_choice_two = None  # Changed to None
        self.player_2_computer_choice_one = None  # Changed to None
        self.player_2_computer_choice_two = None  # Changed to None
        self.player1_choice1_accuracy = None  # Reset player1_choice1_accuracy
        self.player1_choice2_accuracy = None  # Reset player1_choice2_accuracy
        self.player2_choice1_accuracy = None  # Reset player2_choice1_accuracy
        self.player2_choice2_accuracy = None  # Reset player2_choice2_accuracy
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
        self.all_images_displayed = False

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

# -------------------------------------------------------------------------------------------------------------------- #
# ---- MYPAGE: WHERE PLAYERS MAKE THEIR FIRST CHOICE, FIRST BET AND PREFERENCE CHOICES ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class MyPage(Page):
    form_model = 'player'
    form_fields = []

# Get the start time of the page
    @staticmethod
    def js_vars(player: Player):
        return dict(
            page_start_time=int(time.time() * 1000)
        )

# Time players out after 40 seconds spent on MyPage (this assumes that a player has left the session)
    @staticmethod
    def get_timeout_seconds(player: Player):
        return 40

# Time out players who leave the session and set the chosen_image_one based on the manual choice
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.participant.vars['timed_out'] = True

        if player.field_maybe_none('choice1') is None:
            # Set choice1 if it is None (i.e., no manual choice was made)
            player.choice1 = 'left' if player.chosen_image_one == player.left_image else 'right'
        else:
            # Ensure chosen_image_one is set based on the manual choice
            player.chosen_image_one = player.left_image if player.choice1 == 'left' else player.right_image
            player.participant.vars['chosen_image_one'] = player.chosen_image_one
    
# If a player leaves the session, redirect the remaining players to the player_left page

    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        if player.participant.vars.get('timed_out', False):
            return 'player_left'  # This will return 'player_left' if a player leaves

# Define the vars_for_template method to pass variables to the template
# This method is used to pass the left and right images to the template, as well as the player's ID and avatar image

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
        group = player.group
        players = group.get_players()
        response = {}

        # Record the page load time for each player and set the group-level variable when all players have loaded the page
        # This is used to set the round reward and start the choice phase timer
        if 'my_page_load_time' in data:
            player.my_page_load_time = round(data['my_page_load_time'] / 1000, 2)

            if all(p.field_maybe_none('my_page_load_time') for p in players):
                group.my_page_load_time = round(max(p.my_page_load_time for p in players), 2)
                # Set the round reward at the start of each round
                group.set_round_reward()
                # Call the reversal_learning method at the start of each round
                group.reversal_learning()
                # Start the choice phase timer for 4000ms
                player.participant.vars['choice_phase_start_time'] = time.time()  # Record the start time of the choice phase
                print(f"Choice phase timer started for all players in the group")
                return {p.id_in_group: dict(start_choice_phase_timer=True) for p in players}

        # Record the choice made by the player and set the chosen_image_one based on the choice
        # This is used to calculate comparisons and accuracies for the first choice
        if 'initial_choice_time' in data:
            player.initial_choice_time = round(data['initial_choice_time'] / 1000, 2)
            if 'choice' in data and not player.field_maybe_none('chosen_image_one'):
                player.choice1 = data['choice']  # Record the manual choice
                player.chosen_image_one = player.left_image if data['choice'] == 'left' else player.right_image
                player.participant.vars['chosen_image_one'] = player.chosen_image_one
                player.computer_choice_one = False  # Record that the choice was made by the player
                print(f"Player {player.id_in_group} choice1: {player.choice1}, chosen_image_one: {player.chosen_image_one}")

        # Record the choice made by the player and set the chosen_image_one based on the choice
        # This is used to calculate comparisons and accuracies for the first choice
        if 'choice_phase_timer_ended' in data:
            print(f"Choice phase timer ended for all players in the group")

            # Record the choice made by the player and set the chosen_image_one based on the choice
            # This is used to calculate comparisons and accuracies for the first choice 
            for p in players:
                if p.field_maybe_none('choice1') is None or p.choice1 == '':
                    random_choice = random.choice(['left', 'right'])
                    p.choice1 = random_choice
                    p.chosen_image_one = p.left_image if random_choice == 'left' else p.right_image
                    p.participant.vars['chosen_image_one'] = p.chosen_image_one
                    p.initial_choice_time = 4.0  # Record as 4.0 if the choice was made randomly
                    p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 0
                    p.computer_choice_one = True  # Record that the choice was made by the computer
                    if p.chosen_image_one == 'option1A.bmp':
                        p.chosen_image_computer = 'option1A_tr.bmp'
                    elif p.chosen_image_one == 'option1B.bmp':
                        p.chosen_image_computer = 'option1B_tr.bmp'
                    p.choice1_accuracy = p.chosen_image_one == group.seventy_percent_image
                    print(f"Player {p.id_in_group} did not make a choice within 4000ms. Computer randomly selected: choice1: {p.choice1}, chosen_image_one: {p.chosen_image_one}")
                else:
                    p.chosen_image_one = p.left_image if p.choice1 == 'left' else p.right_image
                    p.participant.vars['chosen_image_one'] = p.chosen_image_one
                    p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 0
                    p.choice1_accuracy = p.chosen_image_one == group.seventy_percent_image

            # Calculate the values for the first choice from the perspective of each player
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

            print("All players have made their initial choice (or time limit reached). Presenting bets.")
            return {p.id_in_group: dict(show_bet_container=True, highlight_selected_choice=p.choice1) for p in players}

        # Show the bet container and start the bet phase timer after all players have made their first choice
        if 'show_bet_container' in data and data['show_bet_container']:
            # Calculate comparisons for the first choice
            for p in players:
                p.calculate_choice_comparisons()

            # Start a timer for 4000ms
            player.participant.vars['bet_timer_started'] = True
            player.participant.vars['bet_phase_start_time'] = time.time()  # Record the start time of the bet phase
            print(f"Player {player.id_in_group}: Bet timer started")
            return {player.id_in_group: dict(start_bet_timer=True)}

        # Record the bet made by the player and set the bet1 based on the choice
        if 'bet' in data:
            if not player.field_maybe_none('bet1') and data.get('id') == player.id_in_group:
                player.bet1 = int(data['bet'])
                player.participant.vars['bet1'] = player.bet1
                player.initial_bet_time = round(data['initial_bet_time'] / 1000, 2)
                if player.computer_bet_one != 0:
                    player.computer_bet_one = 0
                print(f"Player {player.id_in_group} made a bet of {player.bet1}, at {player.initial_bet_time}")

                if all(p.field_maybe_none('bet1') != 0 for p in players):
                    player.group.manual_bets = True

        # When the bet timer ends, randomly assign a bet to players who haven't made a bet and start the preference choice phase
        if 'bet_timer_ended' in data:
            player.participant.vars['bet_timer_started'] = False

            if player.group.manual_bets:
                if player.id_in_group == 1:
                    player.group.get_players()[0].participant.vars['preference_choices_presented'] = True
                    return {p.id_in_group: dict(show_preference_choice=True, hide_bet_title=True, highlight_selected_bet=p.bet1) for p in players}
            else:
                for p in players:
                    if p.field_maybe_none('bet1') == 0:
                        p.computer_bet_one = 1
                        random_bet = random.randint(1, 3)
                        p.bet1 = random_bet
                        p.participant.vars['bet1'] = p.bet1
                        p.initial_bet_time = 4.0
                        print(f"Player {p.id_in_group} did not make a bet within 4000ms. Computer randomly selected a bet of {p.bet1}, initial_bet_time: {p.initial_bet_time}")

                if player.id_in_group == 1:
                    player.group.get_players()[0].participant.vars['preference_choices_presented'] = True
                    return {p.id_in_group: dict(show_preference_choice=True, hide_bet_title=True, highlight_selected_bet=p.bet1) for p in players}

        # Record the preference choice made by the player and start the preference choice timer
        if 'preference_choice' in data:
            preference_choice = data['preference_choice']
            if preference_choice in ['1', '2', '3', '4']:
                player.preference_choice = preference_choice
                player.preference_choice_made = True
                player.computer_preference_choice_one = False
                player.preference_choice_time = round(data['preference_choice_time'] / 1000, 2)
                print(f"Player {player.id_in_group} preference_choice: {player.preference_choice}")
                
                # Highlight the selected avatar immediately
                selected_player_id = player.get_others_in_group()[int(player.preference_choice) - 1].id_in_group
                return {player.id_in_group: dict(highlight_selected_avatar=selected_player_id)}
            else:
                pass

        if 'preference_choice_timer_started' in data:
            pass

        if 'preference_choice_button_pressed' in data:
            player.preference_choice = data['preference_choice_button_pressed']
            player.preference_choice_made = True
            player.computer_preference_choice_one = False  # Record that the choice was made by the player
            player.preference_choice_time = round(data['preference_choice_time'] / 1000, 2)
            print(f"Player {player.id_in_group} preference_choice assigned: {player.preference_choice}")

            selected_player = player.get_others_in_group()[int(player.preference_choice) - 1]
            print(f"Player {player.id_in_group} selected initial preference: {player.preference_choice}. Recorded {selected_player.chosen_image_one}")

            if all(p.preference_choice != '0' for p in players):
                player.group.manual_preference_choices = True

            # Highlight the selected avatar immediately
            selected_player_id = selected_player.id_in_group
            response = {player.id_in_group: dict(highlight_selected_avatar=selected_player_id)}
            return response

        # When the preference choice timer ends, randomly assign a preference choice to players who haven't made a choice
        if 'preference_choice_timer_ended' in data:
            for p in players:
                if p.preference_choice == '0':
                    p.preference_choice_time = 4.0
                    # Randomly assign '1' or '2' to preference_choice for players who haven't made a choice
                    p.preference_choice = random.choice(['1', '2', '3', '4'])
                    p.preference_choice_made = True
                    p.computer_preference_choice_one = True  # Record that the choice was made by the computer
                    print(f"Player {p.id_in_group} did not make a preference choice within 4000ms. Computer randomly selected: {p.preference_choice}")
                    
                    # Highlight the selected avatar for players whose choice was made randomly
                    selected_player_id = p.get_others_in_group()[int(p.preference_choice) - 1].id_in_group
                    return {p.id_in_group: dict(highlight_selected_avatar=selected_player_id)}
                else:
                    pass

            # When all players have made a preference choice, display the selected avatar for each player
            if all(p.preference_choice != '0' for p in players):
                if not player.group.preference_choices_presented:
                    player.group.preference_choices_presented = True
                    if player.group.manual_preference_choices:
                        if player.id_in_group == 1:
                            pass
                    else:
                        if player.id_in_group == 1:
                            pass
                    
                    return {p.id_in_group: dict(show_preference_second_choice=True) for p in players}

        # Record the time taken to make the preference choice for each player
        if 'preference_choice_displayed' in data:
            print(f"Preference choices displayed for all players.")
            player.participant.vars['preference_choice_displayed_time'] = round(data['preference_choice_displayed_time'], 2)
            if not player.preference_choice_made:
                # Start a timer for 4000ms
                player.participant.vars['preference_choice_timer_started'] = True
                return {player.id_in_group: dict(start_preference_choice_timer=True)}

        # Record the second preference choice made by the player and start the second preference choice timer
        if 'preference_second_choice' in data:
            preference_second_choice = data['preference_second_choice']
            if preference_second_choice != player.preference_choice and preference_second_choice in ['1', '2', '3', '4']:
                player.preference_second_choice = preference_second_choice
                player.preference_second_choice_made = True
                player.computer_preference_choice_two = False
                player.preference_second_choice_time = round(data['preference_second_choice_time'] / 1000, 2)
                print(f"Player {player.id_in_group} preference_second_choice: {player.preference_second_choice}")
            else:
                pass

        if 'preference_second_choice_button_pressed' in data:
            preference_second_choice = data['preference_second_choice_button_pressed']
            if preference_second_choice != player.preference_choice and preference_second_choice in ['1', '2', '3', '4']:
                if player.field_maybe_none('preference_second_choice') is None or player.preference_second_choice == '0':
                    player.preference_second_choice = preference_second_choice
                    player.preference_second_choice_made = True
                    player.computer_preference_choice_two = False
                    player.preference_second_choice_time = round(data['preference_second_choice_time'] / 1000, 2)
                    print(f"Player {player.id_in_group} preference_second_choice: {player.preference_second_choice}")

                    # Prevent players from selecting the same avatar for both choices
                    selected_player_id = player.get_others_in_group()[int(player.preference_second_choice) - 1].id_in_group
                    return {player.id_in_group: dict(highlight_selected_avatar_second_choice=selected_player_id)}
            else:
                pass

            if all(p.preference_second_choice != '0' for p in players):
                player.group.manual_second_preference_choices = True

        # Display the second preference choice container and start the second preference choice timer
        if 'preference_second_choice_displayed' in data:
            player.participant.vars['preference_second_choice_displayed_time'] = round(data['preference_second_choice_displayed_time'], 2)
            if not player.preference_second_choice_made:
                # Start a timer for 4000ms
                player.participant.vars['preference_second_choice_timer_started'] = True
                return {player.id_in_group: dict(start_preference_second_choice_timer=True)}

        # When the second preference choice timer ends, randomly assign a second preference choice to players who haven't made a choice
        if 'preference_second_choice_timer_ended' in data:
            for p in players:
                if p.preference_second_choice == '0':
                    p.preference_second_choice_time = 4.0
                    available_choices = ['1', '2', '3', '4']
                    available_choices.remove(p.preference_choice)
                    p.preference_second_choice = random.choice(available_choices)
                    p.preference_second_choice_made = True
                    p.computer_preference_choice_two = True
                    print(f"Player {p.id_in_group} did not make a second preference choice within 4000ms. Computer randomly selected: {p.preference_second_choice}")
                    
                    second_selected_player_id = p.get_others_in_group()[int(p.preference_second_choice) - 1].id_in_group
                    response[p.id_in_group] = dict(highlight_selected_avatar_second_choice=second_selected_player_id)

            # Record whether all players have made their second preference choices manually
            if all(p.preference_second_choice != '0' for p in players):
                if player.group.manual_second_preference_choices:
                    if player.id_in_group == 1:
                        pass
                else:
                    if player.id_in_group == 1:
                        pass
                
                # For each player, highlight the selected avatar for the second preference choice 
                for p in players:
                    selected_player_id = p.get_others_in_group()[int(p.preference_choice) - 1].id_in_group
                    selected_player = p.group.get_player_by_id(selected_player_id)
                    chosen_image = selected_player.chosen_image_computer if selected_player.chosen_image_computer else selected_player.chosen_image_one
                    response[p.id_in_group] = {
                        **response.get(p.id_in_group, {}),
                        **dict(
                            display_chosen_image=True,
                            chosen_image=f'main_task/{chosen_image}',
                            selected_player_id=selected_player_id
                        )
                    }
                
                return response

        if 'preference_choice_time' in data:
            player.preference_choice_time = round(data['preference_choice_time'] / 1000, 2)
            if all(p.field_maybe_none('preference_choice_time') for p in players):
                group.all_players_preference_choice_time = round(max(p.preference_choice_time for p in players), 2)

        if 'preference_second_choice_time' in data:
            player.preference_second_choice_time = round(data['preference_second_choice_time'] / 1000, 2)
            if all(p.field_maybe_none('preference_second_choice_time') for p in players):
                group.all_players_preference_second_choice_time = round(max(p.preference_second_choice_time for p in players), 2)

        # Define a method to display the second preference choices for all players
        def display_second_preference_choices(player, players):
            if not player.group.second_preference_choices_displayed:
                player.group.second_preference_choices_displayed = True
                print(f'All players have their first preference images displayed.')
                time.sleep(2)  # Add a 2-second delay
                print(f'Displaying second preference choices.')
                response = {}
                for p in players:
                    selected_player_id = p.get_others_in_group()[int(p.preference_second_choice) - 1].id_in_group
                    selected_player = p.group.get_player_by_id(selected_player_id)
                    chosen_image = selected_player.chosen_image_computer if selected_player.chosen_image_computer else selected_player.chosen_image_one
                    response[p.id_in_group] = dict(
                        display_second_chosen_image=True,
                        second_chosen_image=f'main_task/{chosen_image}',
                        selected_player_id=selected_player_id
                    )
                return response
            return {}

        # Define a method to display all images for all players after the second preference choices are displayed (i.e., the two players not chosen)
        def display_remaining_images(player, players):
            if not player.group.remaining_images_displayed:
                player.group.remaining_images_displayed = True
                print(f'Displaying all images for all players.')
                time.sleep(3)  # Add a 3-second delay
                response = {}
                for p in players:
                    other_players = p.get_others_in_group()
                    all_images = {}
                    for op in other_players:
                        if op.chosen_image_computer:
                            chosen_image = op.chosen_image_computer
                        else:
                            chosen_image = op.chosen_image_one
                        all_images[op.id_in_group] = f'main_task/{chosen_image}'
                    response[p.id_in_group] = dict(
                        display_all_images=True,
                        all_images=all_images
                    )
                pass
                return response
            return {}

        # A series of if statements to handle the display of the second preference choices and all images for all players
        if 'image_displayed' in data:
            player.image_displayed = True

            if all(p.field_maybe_none('image_displayed') for p in players):
                return display_second_preference_choices(player, players)

        if 'second_image_displayed' in data:
            player.second_image_displayed = True

            if all(p.field_maybe_none('second_image_displayed') for p in players):
                return display_remaining_images(player, players)

        if 'all_images_displayed' in data:
            player.all_images_displayed = True

            if all(p.field_maybe_none('all_images_displayed') for p in players):
                if not group.redirect_triggered:
                    group.redirect_triggered = True
                    print('All images displayed for all players, triggering redirect')
                    return {p.id_in_group: dict(redirect_to_second_choice=True) for p in players}

        return response

# -------------------------------------------------------------------------------------------------------------------- #
# ---- SECOND CHOICE PAGE: WHERE PLAYERS MAKE THEIR SECOND CHOICE, SECOND BET AND GET FEEDBACK ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class SecondChoicePage(Page):
    form_model = 'player'
    form_fields = ['choice2', 'bet2']

    # Get the variables for the template and pass them so they can be displayed (i.e., left and right images, player ID, etc.)
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players = group.get_players()
        chosen_images = {
            p.id_in_group: f"main_task/{p.field_maybe_none('chosen_image_computer') or p.field_maybe_none('chosen_image_one') or 'default_image.png'}" 
            for p in players
        }
        other_players = player.get_others_in_group()
        previous_choice = player.participant.vars.get('chosen_image_one')

        return {
            'left_image': f'main_task/{player.left_image}',
            'right_image': f'main_task/{player.right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': [p.id_in_group for p in other_players],
            'chosen_images': chosen_images,
            'previous_choice': previous_choice,
            'previous_bet': player.participant.vars.get('bet1'),
            'round_number': player.round_number,
        }

    # Before the next page, set the choice2 based on the chosen_image_two value if it's not already set
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Set choice2 based on the chosen_image_two value if it's not already set
        if not player.field_maybe_none('choice2'):
            player.choice2 = 'left' if player.chosen_image_two == player.left_image else 'right'
            player.choice2_computer = player.choice2 if player.computer_choice_two else ''


# -------------------------------------------------------------------------------------------------------------------- #
# -------- The live_method: Used to handle real-time data from the players and progress them through the task--------- #
# -------------------------------------------------------------------------------------------------------------------- #

    @staticmethod
    def live_method(player, data):
        group = player.group
        players = group.get_players()

        # Record the time taken to load the second choice page for each player and set the group-level variable when all players have loaded the page
        if 'second_choice_page_loaded' in data:
            player.second_choice_page_load_time = round(data['page_load_time'] / 1000, 2)
            if all(p.field_maybe_none('second_choice_page_load_time') for p in players):
                return {p.id_in_group: dict(start_second_choice_timer=True) for p in players}

        # Record the second choice made by the player and set the chosen_image_two based on the choice
        if 'second_choice' in data:
            player.chosen_image_two = data['second_choice']
            player.choice2 = 'left' if player.chosen_image_two == player.left_image else 'right'
            player.choice2_computer = ''
            player.computer_choice_two = False
            if 'second_choice_time' in data:
                player.second_choice_time = round(data['second_choice_time'] / 1000, 2)
            else:
                player.second_choice_time = None
            print(f"Player {player.id_in_group} made a second choice: {player.choice2} at {player.second_choice_time}")

        # Start the second choice timer for all players and assign a random choice to players who haven't made a choice within the time limit
        if 'second_choice_timer_ended' in data:
            print(f"Second choice timer ended for round {player.round_number}")
            for p in players:
                if p.field_maybe_none('chosen_image_two') is None:
                    random_image = random.choice([p.left_image, p.right_image])
                    p.chosen_image_two = random_image
                    p.choice2 = 'left' if random_image == p.left_image else 'right'
                    p.choice2_computer = p.choice2
                    p.chosen_image_two_binary = 1 if p.chosen_image_two == 'option1A.bmp' else 0
                    p.computer_choice_two = True
                    if p.chosen_image_two == 'option1A.bmp':
                        p.chosen_image_computer_two = 'option1A_tr.bmp'
                    elif p.chosen_image_two == 'option1B.bmp':
                        p.chosen_image_computer_two = 'option1B_tr.bmp'
                    p.second_choice_time = 4.0
                    print(f"Player {p.id_in_group} assigned random second choice: {p.choice2} in round {p.round_number}")
                else:
                    p.chosen_image_two_binary = 1 if p.chosen_image_two == 'option1A.bmp' else 0
                    p.choice2_computer = p.choice2

                p.choice2_accuracy = p.chosen_image_two == p.group.seventy_percent_image
                p.switch_vs_stay = 1 if p.chosen_image_one != p.chosen_image_two else 0

            # Calculate the values for the second choice from the perspective of each player and display the bet container
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

            if not player.group.bet_container_displayed:
                player.group.bet_container_displayed = True
                return {p.id_in_group: dict(show_bet_container=True, start_second_bet_timer=True, highlight_selected_image=p.chosen_image_two) for p in players}


        # Record the bet made by the player and set the bet2 based on the choice if it's not already set 
        if 'second_bet' in data:
            player.bet2 = int(data['second_bet'])
            player.bet2_computer = player.bet2
            player.computer_bet_two = False
            player.second_bet_time = round(data['second_bet_time'] / 1000, 2)
            print(f"Player {player.id_in_group} made a second bet: {player.bet2} at {player.second_bet_time}")

        # Start the second bet timer for all players and assign a random bet to players who haven't made a bet within the time limit
        if 'second_bet_timer_ended' in data:
            # Calculate comparisons for the first choice
            for p in players:
                p.calculate_choice_comparisons()
                
            if not group.second_bet_timer_ended_executed:
                for p in players:
                    if p.bet2 == 0:
                        random_bet = random.randint(1, 3)
                        p.bet2 = random_bet
                        p.bet2_computer = p.bet2
                        p.computer_bet_two = True
                        p.second_bet_time = 4.0
                        print(f"Player {p.id_in_group} did not make a second bet within the time limit. Computer assigned bet: {p.bet2}")

                # Calculate trial_reward and trial_earnings for each player
                for p in players:
                    if p.chosen_image_two == 'option1A.bmp':
                        p.trial_reward = group.round_reward_A
                    else:
                        p.trial_reward = group.round_reward_B
                    
                    p.trial_earnings = p.bet2_computer * 20 * p.trial_reward if p.trial_reward == 1 else -1 * p.bet2_computer * 20
                    p.total_reward_earnings = sum([prev_player.trial_earnings for prev_player in p.in_previous_rounds()]) + p.trial_earnings
                    p.loss_or_gain = -1 if p.trial_earnings < 0 else 1

                # Calculate loss_or_gain for other players in the group from the perspective of each player
                for p in players:
                    other_players = p.get_others_in_group()
                    p.loss_or_gain_player1 = 0 if other_players[0].trial_earnings < 0 else 1
                    p.loss_or_gain_player2 = 0 if other_players[1].trial_earnings < 0 else 1
                    p.loss_or_gain_player3 = 0 if other_players[2].trial_earnings < 0 else 1
                    p.loss_or_gain_player4 = 0 if other_players[3].trial_earnings < 0 else 1

                # Print display phase information for each player 
                # This includes chosen_image_two, trial_reward, trial_earnings, and total_reward_earnings
                for p in players:
                    print(f"Player {p.id_in_group} display phase - chosen_image_two: {p.chosen_image_two}, trial_reward: {p.trial_reward}, trial_earnings: {p.trial_earnings}, total_reward_earnings: {p.total_reward_earnings}")

                # Generate the intertrial interval and set the next round transition time
                group.generate_intertrial_interval()
                group.next_round_transition_time = time.time() * 1000 + group.intertrial_interval

                group.second_bet_timer_ended_executed = True

                chosen_images_secondchoicepage = {p.id_in_group: f"main_task/{p.chosen_image_computer_two}" if p.chosen_image_computer_two else f"main_task/{p.chosen_image_two}" for p in players}
                win_loss_images = {p.id_in_group: f'main_task/{"win" if p.trial_reward == 1 else "loss"}.bmp' for p in players}

                return {
                    p.id_in_group: dict(
                        show_results=True,
                        second_bet_reward=p.trial_earnings,
                        chosen_images=chosen_images_secondchoicepage,
                        win_loss_images=win_loss_images,
                        player_win_loss_image=win_loss_images[p.id_in_group],
                        intertrial_interval=group.intertrial_interval,
                        round_number=player.round_number,
                        num_rounds=C.NUM_ROUNDS
                    ) for p in players
                }

        return {}

# -------------------------------------------------------------------------------------------------------------------- #
# ---- FINAL RESULTS PAGE: AFTER 100 ROUNDS, PLAYERS RECEIVE THEIR POINTS TALLY ------ #
# -------------------------------------------------------------------------------------------------------------------- #

class FinalResults(Page):

    # Only display the final results page after 100 rounds have been completed
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    # Get the variables for the template and pass them so they can be displayed (i.e., total_reward_earnings and player ID)
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'total_reward_earnings': player.total_reward_earnings,
            'player_id': player.id_in_group,
        }

    # Redirect players to the submission page after the final results page so they can return to Prolific
    @staticmethod
    def app_after_this_page(player, upcoming_apps):
        print('upcoming_apps is', upcoming_apps)
        return "submission"  # Hardcoded name of the last app

page_sequence = [MyPage, SecondChoicePage, FinalResults]  

# -------------------------------------------------------------------------------------------------------------------- #