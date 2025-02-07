# submission app for social-influence-task

# This app collects feedback from participants after they complete the main task.
# The feedback is used to assess the participant's understanding of the task and their engagement.
# It also stores the bonus payment from the main task and the participant's ranking of other players.

# We take the players Prolific ID from earlier and display it before submission, for the Qualtrics survey.

from otree.api import *

# Constants class defining game-wide settings
class C(BaseConstants):
    NAME_IN_URL = 'submission'    # URL segment for submission app
    PLAYERS_PER_GROUP = None      # Individual decision-making
    NUM_ROUNDS = 1                # Single round game

# Model classes
class Subsession(BaseSubsession):
    pass  # No subsession-level data needed

class Group(BaseGroup):
    pass  # No group-level data needed

class Player(BasePlayer):
    # Store variables from previous apps to help with assigning bonuses (bonus payment, Prolific ID)
    main_task_bonus = models.CurrencyField()  # Store the bonus from main task
    prolific_id = models.StringField()  # Store participant's Prolific ID

    # Survey questions using 0-100 scale
    task_understanding = models.IntegerField(min=0, max=100)  # Understanding of experiment
    task_difficulty = models.IntegerField(min=0, max=100)  # Task difficulty rating
    engagement = models.IntegerField(min=0, max=100)          # Level of engagement
    influence = models.IntegerField(min=0, max=100)           # Perceived influence
    real_players = models.IntegerField(min=0, max=100)        # Belief about real players
    attention_focus = models.IntegerField(min=0, max=100)     # Attention level

    additional_feedback = models.LongStringField(blank=True)  # Additional comments (optional)
    
    # Player ranking fields - storing participant codes
    ranking_first = models.StringField()     # Most influential player's participant code
    ranking_second = models.StringField()    # Second most influential participant code
    ranking_third = models.StringField()     # Third most influential participant code
    ranking_fourth = models.StringField()    # Least influential participant code
    
    # Main task reference fields
    main_task_player_id = models.IntegerField()  # Player's ID from main task
    main_task_group_id = models.IntegerField()   # Group's ID from main task

    # Choice earnings sums
    choice1_sum_earnings = models.IntegerField()  # Sum of earnings from first choices
    choice2_sum_earnings = models.IntegerField()  # Sum of earnings from second choices

    # Choice accuracy and reward sums
    choice1_accuracy_sum = models.IntegerField()  # Sum of accurate first choices
    choice2_accuracy_sum = models.IntegerField()  # Sum of accurate second choices
    choice1_reward_binary_sum = models.IntegerField()  # Sum of correct first choices
    choice2_reward_binary_sum = models.IntegerField()  # Sum of correct second choices

    def get_prolific_id(self):
        # Retrieve stored Prolific ID from participant vars
        return self.participant.vars.get('prolific_id', '')

def creating_session(subsession):
    # Initialize completion status for all players
    for p in subsession.get_players():
        p.participant.finished = False

# Page classes
class Feedback(Page):
    form_model = 'player'
    # Fields to collect in feedback form
    form_fields = [
        'task_understanding',
        'task_difficulty', 
        'engagement', 
        'influence', 
        'real_players', 
        'attention_focus', 
        'ranking_first',
        'ranking_second',
        'ranking_third',
        'ranking_fourth',
        'additional_feedback'
    ]

    # Get the player and group IDs from the main task to map their rankings 
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Store main task IDs
        player.main_task_player_id = player.participant.vars.get('main_task_player_id')
        player.main_task_group_id = player.participant.vars.get('main_task_group_id')

        # Store bonus from main task
        player.main_task_bonus = player.participant.vars.get('bonus_payoff', cu(0))

        # Store the prolific ID
        player.prolific_id = player.get_prolific_id()

        # Retrieve the earnings sums from participant.vars
        player.choice1_sum_earnings = player.participant.vars.get('choice1_sum_earnings', 0)
        player.choice2_sum_earnings = player.participant.vars.get('choice2_sum_earnings', 0)

        # Retrieve the choice sums from participant.vars
        player.choice1_accuracy_sum = player.participant.vars.get('choice1_accuracy_sum', 0)
        player.choice2_accuracy_sum = player.participant.vars.get('choice2_accuracy_sum', 0)
        player.choice1_reward_binary_sum = player.participant.vars.get('choice1_reward_binary_sum', 0)
        player.choice2_reward_binary_sum = player.participant.vars.get('choice2_reward_binary_sum', 0)

    @staticmethod
    def vars_for_template(player):
        # Get main task data
        main_task_player_id = player.participant.vars.get('main_task_player_id')
        main_task_group_id = player.participant.vars.get('main_task_group_id')
        
        # Get the player's group from the main task app
        main_task_groups = player.session.vars.get('main_task_groups', {})
        
        main_task_players = main_task_groups.get(str(main_task_group_id), [])
        
        # Filter out the current player and get other players' data
        other_players = [p for p in main_task_players if p['id_in_group'] != main_task_player_id]
        
        # Create mapping of display numbers to participant codes
        player_mapping = {
            f"Player {i+1}": p['participant_code'] 
            for i, p in enumerate(other_players)
        }

        return {
            'main_task_player_id': main_task_player_id,
            'main_task_group_id': main_task_group_id,
            'player_mapping': player_mapping
        }

# Submission page with completion link
# We take the Prolific ID from earlier and display it before submission, for the Qualtrics survey.    
class Submit(Page):
    @staticmethod
    def js_vars(player):
        # Pass completion URL to JavaScript
        return dict(
            completionlink=player.session.config['completionlink']
        )
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Mark participant as finished
        player.participant.finished = True

    @staticmethod
    def vars_for_template(player):
        # Pass Prolific ID to template
        return {
            'prolific_id': player.get_prolific_id()
        }

# Define sequence of pages
page_sequence = [Feedback, Submit]