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
    # Survey questions using 0-100 scale
    task_understanding = models.IntegerField(min=0, max=100)  # Understanding of experiment
    engagement = models.IntegerField(min=0, max=100)          # Level of engagement
    influence = models.IntegerField(min=0, max=100)           # Perceived influence
    real_players = models.IntegerField(min=0, max=100)        # Belief about real players
    attention_focus = models.IntegerField(min=0, max=100)     # Attention level
    
    # Player ranking fields - storing participant codes
    ranking_first = models.StringField()     # Most influential player's participant code
    ranking_second = models.StringField()    # Second most influential participant code
    ranking_third = models.StringField()     # Third most influential participant code
    ranking_fourth = models.StringField()    # Least influential participant code
    
    # Main task reference fields
    main_task_player_id = models.IntegerField()  # Player's ID from main task
    main_task_group_id = models.IntegerField()   # Group's ID from main task

    additional_feedback = models.LongStringField(blank=True)  # Additional comments (optional)

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

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Store main task IDs
        player.main_task_player_id = player.participant.vars.get('main_task_player_id')
        player.main_task_group_id = player.participant.vars.get('main_task_group_id')

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