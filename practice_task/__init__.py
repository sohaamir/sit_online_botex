from otree.api import *
from otree.live import live_payload_function
import random
import time

doc = """
Practice social influence task with 10 trials and fixed reward probabilities.
"""

class C(BaseConstants):
    NAME_IN_URL = 'practice_task'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 3
    REWARD_PROBABILITY_A = 0.7
    REWARD_PROBABILITY_B = 0.3
    IMAGES = ['option1A.bmp', 'option1B.bmp']
    AVATAR_IMAGE = 'practice_task/avatar_male.png'
    IMAGE_PATHS = {
        'option1A.bmp': '_static/practice_task/option1A.bmp',
        'option1B.bmp': '_static/practice_task/option1B.bmp',
        'option1A_tr.bmp': '_static/practice_task/option1A_tr.bmp',
        'option1B_tr.bmp': '_static/practice_task/option1B_tr.bmp',
        'avatar_male.png': '_static/practice_task/avatar_male.png',
    }

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    current_round = models.IntegerField(initial=1)
    my_page_load_time = models.FloatField()
    round_reward_A = models.IntegerField()
    round_reward_B = models.IntegerField()
    second_choice_timer_started = models.BooleanField(initial=False)
    all_players_made_choice2 = models.BooleanField(initial=False)
    all_manual_bet2 = models.BooleanField(initial=False)    
    intertrial_interval = models.IntegerField(initial=0)
    manual_bets = models.BooleanField(initial=False)
    manual_preference_choices = models.BooleanField(initial=False)
    manual_second_preference_choices = models.BooleanField(initial=False)
    show_results_sent = models.BooleanField(initial=False)
    show_results_executed = models.BooleanField(initial=False)
    second_bet_timer_ended_executed = models.BooleanField(initial=False)
    next_round_transition_time = models.FloatField()
    redirect_triggered = models.BooleanField(initial=False)
    second_preference_choices_displayed = models.BooleanField(initial=False)

    def set_round_reward(self):
        self.round_reward_A = 1 if random.random() < C.REWARD_PROBABILITY_A else 0
        self.round_reward_B = 1 if random.random() < C.REWARD_PROBABILITY_B else 0

    def set_payoffs(self):
        for p in self.get_players():
            if p.chosen_image_two == 'option1A.bmp':
                p.trial_reward = self.round_reward_A
            else:
                p.trial_reward = self.round_reward_B

            p.trial_earnings = p.bet2_computer * 20 * p.trial_reward
            p.total_reward_earnings += p.trial_earnings

    def generate_intertrial_interval(self):
        self.intertrial_interval = random.randint(2000, 4000)
        print(f"Intertrial interval of {self.intertrial_interval}ms generated")

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

class Player(BasePlayer):
    choice1 = models.StringField(initial='')
    choice2 = models.StringField(initial='')
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
    chosen_image_computer = models.StringField(initial='')
    chosen_image_computer_two = models.StringField(initial='')
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
    computer_choice_one = models.BooleanField(initial=True)
    computer_bet_one = models.IntegerField(initial=1)
    computer_preference_choice_one = models.BooleanField(initial=True)
    button_pressed = models.BooleanField(initial=False)
    computer_preference_choice_two = models.BooleanField(initial=True)
    computer_choice_two = models.BooleanField(initial=True)
    computer_bet_two = models.BooleanField(initial=False)
    player_1_choice_one = models.IntegerField()
    player_1_choice_two = models.IntegerField()
    player_2_choice_one = models.IntegerField()
    player_2_choice_two = models.IntegerField()
    player_1_computer_choice_one = models.BooleanField()
    player_1_computer_choice_two = models.BooleanField()
    player_2_computer_choice_one = models.BooleanField()
    player_2_computer_choice_two = models.BooleanField()

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
        self.chosen_image_computer = ''
        self.chosen_image_computer_two = ''
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

# PAGES 
class MyPage(Page):
    form_model = 'player'
    form_fields = []

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.field_maybe_none('choice1') is None:
            # Set choice1 if it is None (i.e., no manual choice was made)
            player.choice1 = 'left' if player.chosen_image_one == player.left_image else 'right'
        else:
            # Ensure chosen_image_one is set based on the manual choice
            player.chosen_image_one = player.left_image if player.choice1 == 'left' else player.right_image
            player.participant.vars['chosen_image_one'] = player.chosen_image_one

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
            'left_image': f'practice_task/{left_image}',
            'right_image': f'practice_task/{right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': [p.id_in_group for p in other_players],
        }

    @staticmethod
    def live_method(player, data):
        group = player.group
        players = group.get_players()

        if 'my_page_load_time' in data:
            player.my_page_load_time = round(data['my_page_load_time'] / 1000, 2)

            if all(p.field_maybe_none('my_page_load_time') for p in players):
                group.my_page_load_time = round(max(p.my_page_load_time for p in players), 2)
                # Set the round reward at the start of each round
                group.set_round_reward()
                # Start the choice phase timer for 2000ms
                player.participant.vars['choice_phase_start_time'] = time.time()  # Record the start time of the choice phase
                print(f"Choice phase timer started for all players in the group")
                return {p.id_in_group: dict(start_choice_phase_timer=True) for p in players}

        if 'initial_choice_time' in data:
            player.initial_choice_time = round(data['initial_choice_time'] / 1000, 2)
            if 'choice' in data and not player.field_maybe_none('chosen_image_one'):
                player.choice1 = data['choice']  # Record the manual choice
                player.chosen_image_one = player.left_image if data['choice'] == 'left' else player.right_image
                player.participant.vars['chosen_image_one'] = player.chosen_image_one
                player.computer_choice_one = False  # Record that the choice was made by the player
                print(f"Player {player.id_in_group} choice1: {player.choice1}, chosen_image_one: {player.chosen_image_one}")

        if 'choice_phase_timer_ended' in data:
            print(f"Choice phase timer ended for all players in the group")

            for p in players:
                if p.field_maybe_none('choice1') is None or p.choice1 == '':
                    random_choice = random.choice(['left', 'right'])
                    p.choice1 = random_choice
                    p.chosen_image_one = p.left_image if random_choice == 'left' else p.right_image
                    p.participant.vars['chosen_image_one'] = p.chosen_image_one
                    p.initial_choice_time = 2.0  # Record as 2.0 if the choice was made randomly
                    p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 0
                    p.computer_choice_one = True  # Record that the choice was made by the computer
                    if p.chosen_image_one == 'option1A.bmp':
                        p.chosen_image_computer = 'option1A_tr.bmp'
                    elif p.chosen_image_one == 'option1B.bmp':
                        p.chosen_image_computer = 'option1B_tr.bmp'
                    print(f"Player {p.id_in_group} did not make a choice within 2000ms. Computer randomly selected: choice1: {p.choice1}, chosen_image_one: {p.chosen_image_one}")
                else:
                    p.chosen_image_one = p.left_image if p.choice1 == 'left' else p.right_image
                    p.participant.vars['chosen_image_one'] = p.chosen_image_one
                    p.chosen_image_one_binary = 1 if p.chosen_image_one == 'option1A.bmp' else 0

            for p in players:
                other_players = p.get_others_in_group()
                p.player_1_choice_one = other_players[0].chosen_image_one_binary
                p.player_2_choice_one = other_players[1].chosen_image_one_binary
                p.player_1_computer_choice_one = other_players[0].computer_choice_one
                p.player_2_computer_choice_one = other_players[1].computer_choice_one

            print("All players have made their initial choice (or time limit reached). Presenting bets.")
            return {p.id_in_group: dict(show_bet_container=True, highlight_selected_choice=p.choice1) for p in players}

        if 'show_bet_container' in data and data['show_bet_container']:
            # Start a timer for 2000ms
            player.participant.vars['bet_timer_started'] = True
            player.participant.vars['bet_phase_start_time'] = time.time()  # Record the start time of the bet phase
            print(f"Player {player.id_in_group}: Bet timer started")
            return {player.id_in_group: dict(start_bet_timer=True)}

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

        if 'bet_timer_ended' in data:
            player.participant.vars['bet_timer_started'] = False

            if player.group.manual_bets:
                if player.id_in_group == 1:
                    pass
                player.group.get_players()[0].participant.vars['preference_choices_presented'] = True
                return {p.id_in_group: dict(show_preference_choice=True, hide_bet_title=True, highlight_selected_bet=p.bet1) for p in players}
            else:
                for p in players:
                    if p.field_maybe_none('bet1') == 0:
                        p.computer_bet_one = 1
                        random_bet = random.randint(1, 3)
                        p.bet1 = random_bet
                        p.participant.vars['bet1'] = p.bet1
                        p.initial_bet_time = 2.0
                        print(f"Player {p.id_in_group} did not make a bet within 2000ms. Computer randomly selected a bet of {p.bet1}, initial_bet_time: {p.initial_bet_time}")

                if player.id_in_group == 1:
                    pass

                player.group.get_players()[0].participant.vars['preference_choices_presented'] = True
                return {p.id_in_group: dict(show_preference_choice=True, hide_bet_title=True, highlight_selected_bet=p.bet1) for p in players}

        if 'preference_choice' in data:
            preference_choice = data['preference_choice']
            if preference_choice in ['1', '2']:
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

        if 'preference_choice_timer_ended' in data:
            for p in players:
                if p.preference_choice == '0':
                    p.preference_choice_time = 2.0
                    # Randomly assign '1' or '2' to preference_choice for players who haven't made a choice
                    p.preference_choice = random.choice(['1', '2'])
                    p.preference_choice_made = True
                    p.computer_preference_choice_one = True  # Record that the choice was made by the computer
                    print(f"Player {p.id_in_group} did not make a preference choice within 2000ms. Computer randomly selected: {p.preference_choice}")
                    
                    # Highlight the selected avatar for players whose choice was made randomly
                    selected_player_id = p.get_others_in_group()[int(p.preference_choice) - 1].id_in_group
                    return {p.id_in_group: dict(highlight_selected_avatar=selected_player_id)}
                else:
                    pass

            if all(p.preference_choice != '0' for p in players):
                if player.group.manual_preference_choices:
                    if player.id_in_group == 1:
                        pass
                else:
                    if player.id_in_group == 1:
                        pass
                
                player.group.get_players()[0].participant.vars['preference_choices_presented'] = True
                return {p.id_in_group: dict(show_preference_second_choice=True) for p in players}

        if 'preference_choice_displayed' in data:
            print(f"Preference choices displayed for all players.")
            player.participant.vars['preference_choice_displayed_time'] = round(data['preference_choice_displayed_time'], 2)
            if not player.preference_choice_made:
                # Start a timer for 2000ms
                player.participant.vars['preference_choice_timer_started'] = True
                return {player.id_in_group: dict(start_preference_choice_timer=True)}

        if 'preference_second_choice' in data:
            preference_second_choice = data['preference_second_choice']
            if preference_second_choice != player.preference_choice and preference_second_choice in ['1', '2']:
                player.preference_second_choice = preference_second_choice
                player.preference_second_choice_made = True
                player.computer_preference_choice_two = False
                player.preference_second_choice_time = round(data['preference_second_choice_time'] / 1000, 2)
                print(f"Player {player.id_in_group} preference_second_choice: {player.preference_second_choice}")
            else:
                pass

        if 'preference_second_choice_button_pressed' in data:
            preference_second_choice = data['preference_second_choice_button_pressed']
            if preference_second_choice != player.preference_choice and preference_second_choice in ['1', '2']:
                if player.field_maybe_none('preference_second_choice') is None or player.preference_second_choice == '0':
                    player.preference_second_choice = preference_second_choice
                    player.preference_second_choice_made = True
                    player.computer_preference_choice_two = False
                    player.preference_second_choice_time = round(data['preference_second_choice_time'] / 1000, 2)
                    print(f"Player {player.id_in_group} preference_second_choice: {player.preference_second_choice}")

                    selected_player_id = player.get_others_in_group()[int(player.preference_second_choice) - 1].id_in_group
                    return {player.id_in_group: dict(highlight_selected_avatar_second_choice=selected_player_id)}
            else:
                pass

            if all(p.preference_second_choice != '0' for p in players):
                player.group.manual_second_preference_choices = True

        if 'preference_second_choice_displayed' in data:
            player.participant.vars['preference_second_choice_displayed_time'] = round(data['preference_second_choice_displayed_time'], 2)
            if not player.preference_second_choice_made:
                # Start a timer for 2000ms
                player.participant.vars['preference_second_choice_timer_started'] = True
                return {player.id_in_group: dict(start_preference_second_choice_timer=True)}

        if 'preference_second_choice_timer_ended' in data:
            response = {}
            for p in players:
                if p.preference_second_choice == '0':
                    p.preference_second_choice_time = 2.0
                    # Assign the remaining value ('1' or '2') to preference_second_choice
                    p.preference_second_choice = '1' if p.preference_choice == '2' else '2'
                    p.preference_second_choice_made = True
                    p.computer_preference_choice_two = True
                    print(f"Player {p.id_in_group} did not make a second preference choice within 2000ms. Computer selected: {p.preference_second_choice}")
                    
                    # Highlight the selected avatar for players whose choice was made randomly
                    second_selected_player_id = p.get_others_in_group()[int(p.preference_second_choice) - 1].id_in_group
                    response[p.id_in_group] = dict(highlight_selected_avatar_second_choice=second_selected_player_id)
                else:
                    pass

            if all(p.preference_second_choice != '0' for p in players):
                if player.group.manual_second_preference_choices:
                    if player.id_in_group == 1:
                        pass
                else:
                    if player.id_in_group == 1:
                        pass
                
                for p in players:
                    selected_player_id = p.get_others_in_group()[int(p.preference_choice) - 1].id_in_group
                    selected_player = p.group.get_player_by_id(selected_player_id)
                    chosen_image = selected_player.chosen_image_computer if selected_player.chosen_image_computer else selected_player.chosen_image_one
                    response[p.id_in_group] = {
                        **response.get(p.id_in_group, {}),
                        **dict(
                            display_chosen_image=True,
                            chosen_image=f'practice_task/{chosen_image}',
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
                        second_chosen_image=f'practice_task/{chosen_image}',
                        selected_player_id=selected_player_id
                    )
                return response
            return {}

        def trigger_redirect_to_second_choice(player, players):
            if not player.group.redirect_triggered:
                player.group.redirect_triggered = True
                print(f'All players have their second preference images displayed.')
                time.sleep(3)  # Add a 3-second delay
                print(f'Sending redirect_to_second_choice event.')
                for p in players:
                    p.participant.vars['preference_choices_displayed'] = True
                return {p.id_in_group: dict(redirect_to_second_choice=True) for p in players}
            return {}

        if 'image_displayed' in data:
            player.image_displayed = True

            if all(p.field_maybe_none('image_displayed') for p in players):
                return display_second_preference_choices(player, players)

        if 'second_image_displayed' in data:
            player.second_image_displayed = True

            if all(p.field_maybe_none('second_image_displayed') for p in players):
                return trigger_redirect_to_second_choice(player, players)

        return {}

class SecondChoicePage(Page):
    form_model = 'player'
    form_fields = ['choice2', 'bet2']

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players = group.get_players()
        chosen_images = {p.id_in_group: f"practice_task/{p.chosen_image_computer if p.chosen_image_computer else p.chosen_image_one}" for p in players}
        other_players = player.get_others_in_group()
        previous_choice = player.participant.vars.get('chosen_image_one')

        return {
            'left_image': f'practice_task/{player.left_image}',
            'right_image': f'practice_task/{player.right_image}',
            'player_id': player.id_in_group,
            'avatar_image': C.AVATAR_IMAGE,
            'other_player_ids': [p.id_in_group for p in other_players],
            'chosen_images': chosen_images,
            'previous_choice': player.participant.vars.get('chosen_image_one'),
            'previous_bet': player.participant.vars.get('bet1'),
            'round_number': player.round_number,
        }

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Set choice2 based on the chosen_image_two value if it's not already set
        if not player.field_maybe_none('choice2'):
            player.choice2 = 'left' if player.chosen_image_two == player.left_image else 'right'

    @staticmethod
    def live_method(player, data):
        group = player.group
        players = group.get_players()

        if 'second_choice_page_loaded' in data:
            player.second_choice_page_load_time = round(data['page_load_time'] / 1000, 2)
            if all(p.field_maybe_none('second_choice_page_load_time') for p in players):
                return {p.id_in_group: dict(start_second_choice_timer=True) for p in players}

        if 'second_choice' in data:
            player.chosen_image_two = data['second_choice']
            player.choice2 = 'left' if player.chosen_image_two == player.left_image else 'right'
            player.computer_choice_two = False
            player.second_choice_time = round(data['second_choice_time'] / 1000, 2)
            print(f"Player {player.id_in_group} made a second choice: {player.choice2} at {player.second_choice_time}")

        if 'second_choice_timer_ended' in data:
            print(f"Second choice timer ended for round {player.round_number}")
            for p in players:
                if p.field_maybe_none('chosen_image_two') is None:
                    random_image = random.choice([p.left_image, p.right_image])
                    p.chosen_image_two = random_image
                    p.choice2 = 'left' if random_image == p.left_image else 'right'
                    p.chosen_image_two_binary = 1 if p.chosen_image_two == 'option1A.bmp' else 0
                    p.computer_choice_two = True
                    if p.chosen_image_two == 'option1A.bmp':
                        p.chosen_image_computer_two = 'option1A_tr.bmp'
                    elif p.chosen_image_two == 'option1B.bmp':
                        p.chosen_image_computer_two = 'option1B_tr.bmp'
                    p.second_choice_time = 2.0
                    print(f"Player {p.id_in_group} assigned random second choice: {p.choice2} in round {p.round_number}")
                else:
                    p.chosen_image_two_binary = 1 if p.chosen_image_two == 'option1A.bmp' else 0

            for p in players:
                other_players = p.get_others_in_group()
                p.player_1_choice_two = other_players[0].chosen_image_two_binary
                p.player_2_choice_two = other_players[1].chosen_image_two_binary
                p.player_1_computer_choice_two = other_players[0].computer_choice_two
                p.player_2_computer_choice_two = other_players[1].computer_choice_two

                p.switch_vs_stay = 1 if p.chosen_image_one != p.chosen_image_two else 0

            return {p.id_in_group: dict(show_bet_container=True, start_second_bet_timer=True, highlight_selected_image=p.chosen_image_two) for p in players}

        if 'second_bet' in data:
            player.bet2 = int(data['second_bet'])
            player.bet2_computer = player.bet2  # Assign the value to bet2_computer
            player.computer_bet_two = False
            player.second_bet_time = round(data['second_bet_time'] / 1000, 2)
            print(f"Player {player.id_in_group} made a second bet: {player.bet2} at {player.second_bet_time}")

            # Check if all players have made their second bet
            if all(p.bet2 != 0 for p in players):
                group.all_manual_bet2 = True
                player.participant.vars['all_manual_bet2'] = True  # Store the flag in participant.vars

        if 'second_bet_timer_ended' in data:
            if not group.second_bet_timer_ended_executed:
                for p in players:
                    if p.bet2 == 0:
                        random_bet = random.randint(1, 3)
                        p.bet2 = random_bet
                        p.bet2_computer = p.bet2  # Assign the value to bet2_computer
                        p.computer_bet_two = True
                        p.second_bet_time = 1.0
                        print(f"Player {p.id_in_group} did not make a second bet within the time limit. Computer assigned bet: {p.bet2}")

                # Calculate trial_reward and trial_earnings based on the round_reward and the player's chosen_image_two
                for p in players:
                    p.chosen_image_two = p.left_image if p.choice2 == 'left' else p.right_image
                    if p.chosen_image_two == 'option1A.bmp':
                        p.trial_reward = group.round_reward_A
                    else:
                        p.trial_reward = group.round_reward_B
                    
                    if p.trial_reward == 1:
                        p.trial_earnings = p.bet2_computer * 20 * p.trial_reward
                    else:
                        p.trial_earnings = -1 * p.bet2_computer * 20
                    
                    # Calculate total_reward_earnings by summing trial_earnings from all previous rounds
                    previous_trial_earnings = [prev_player.trial_earnings for prev_player in p.in_previous_rounds()]
                    p.total_reward_earnings = sum(previous_trial_earnings) + p.trial_earnings
                    
                    # Calculate total_reward_earnings by summing trial_earnings from all previous rounds
                    previous_trial_earnings = [prev_player.trial_earnings for prev_player in p.in_previous_rounds()]
                    p.total_reward_earnings = sum(previous_trial_earnings) + p.trial_earnings

                # Print display phase information only once per round
                if player.id_in_group == 1:
                    for p in players:
                        print(f"Player {p.id_in_group} display phase - chosen_image_two: {p.chosen_image_two}, trial_reward: {p.trial_reward}, trial_earnings: {p.trial_earnings}, total_reward_earnings: {p.total_reward_earnings}")

                # Generate intertrial interval only once for all players in the group
                if player.id_in_group == 1:
                    group.generate_intertrial_interval()
                    group.next_round_transition_time = time.time() * 1000 + group.intertrial_interval

                group.second_bet_timer_ended_executed = True

                chosen_images_secondchoicepage = {
                    p.id_in_group: f"practice_task/{p.chosen_image_computer_two}" if p.chosen_image_computer_two else f"practice_task/{p.chosen_image_two}" for p in players
                }
                win_loss_images = {p.id_in_group: f'practice_task/{"win" if p.trial_reward == 1 else "loss"}.bmp' for p in players}
                player_win_loss_images = {p.id_in_group: f'practice_task/{"win" if p.trial_reward == 1 else "loss"}.bmp' for p in players}

                return {
                    p.id_in_group: dict(
                        show_results=True,
                        second_bet_reward=p.trial_earnings,
                        chosen_images=chosen_images_secondchoicepage,
                        win_loss_images=win_loss_images,
                        player_win_loss_image=player_win_loss_images[p.id_in_group],
                        intertrial_interval=group.intertrial_interval,
                        round_number=player.round_number,
                        num_rounds=C.NUM_ROUNDS
                    ) for p in players
                }

        return {}
        
class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'total_reward_earnings': player.total_reward_earnings,
            'player_id': player.id_in_group,
        }

page_sequence = [MyPage, SecondChoicePage, FinalResults]  