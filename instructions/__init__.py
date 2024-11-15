# instructions/__init__.py

from otree.api import *

# Constants class defining game-wide settings
class C(BaseConstants):
   NAME_IN_URL = 'instructions'  # URL segment for this app
   PLAYERS_PER_GROUP = None      # Individual decision-making (no grouping) 
   NUM_ROUNDS = 1                # Single-round game

# Model classes
class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
   pass  # No group-level data needed 

class Player(BasePlayer):
   prolific_id = models.StringField(blank=True)  # Store Prolific participant IDs

# Page sequence classes
class Welcome(Page):
   pass  # Display welcome message

class Consent(Page):
   @staticmethod              
   def js_vars(player):
       # Pass no-consent redirect URL to JavaScript
       return dict(
           noconsentlink=player.subsession.session.config['noconsentlink']
       )
   pass

class TaskOverview(Page):
   @staticmethod
   def before_next_page(player, timeout_happened):
       # Store Prolific ID from participant label
       if player.participant.label is not None:
           player.prolific_id = player.participant.label
           player.participant.vars['prolific_id'] = player.prolific_id
       else:
           # Handle missing participant label
           player.prolific_id = "No ID provided"
           player.participant.vars['prolific_id'] = player.prolific_id

class TaskInstructionsPage1(Page):
   pass  # Display first page of task instructions

class TaskInstructionsPage2(Page): 
   pass  # Display second page of task instructions

class RewardStructure(Page):
   pass  # Display information about rewards/payments

class Leaving(Page):
   pass  # Display information about early withdrawal

class Comprehension(Page):
   pass  # Display comprehension check questions

class AdjustDimensions(Page):
   pass  # Display instructions for adjusting display dimensions

class PracticeInstructions(Page):
   pass  # Display instructions for practice round

class FixDimensions(Page):
    pass  # Simple page to let players adjust their display dimensions

# Define sequence of pages shown to participants
page_sequence = [Welcome, Consent, TaskOverview, TaskInstructionsPage1, 
                TaskInstructionsPage2, RewardStructure, Leaving, 
                Comprehension, AdjustDimensions, FixDimensions, 
                PracticeInstructions]