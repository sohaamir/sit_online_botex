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
   form_fields = ['task_understanding', 'engagement', 'influence', 'real_players', 'attention_focus', 'additional_feedback']

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