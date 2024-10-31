from otree.api import *

# Constants class defining game-wide settings
class C(BaseConstants):
   NAME_IN_URL = 'instructions'  # URL segment for this app
   PLAYERS_PER_GROUP = None      # Individual decision-making (no grouping) 
   NUM_ROUNDS = 1                # Single-round game
   TRANSITION_TIME = 15          # Seconds to wait before practice task

# Model classes
class Subsession(BaseSubsession):
   pass  # No subsession-level data needed

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

class PracticeInstructions(Page):
   pass  # Display instructions for practice round

class WaitPage1(WaitPage):
   template_name = 'instructions/WaitPage1.html'  # Custom wait page template

   @staticmethod
   def is_displayed(player: Player):
       return player.round_number == 1  # Only show in first round
   
   @staticmethod
   def vars_for_template(player):
       # Pass title text to template
       return {
           'title_text': 'Waiting for Other Players',
       }
   
   @staticmethod              
   def js_vars(player):
       # Pass waitpage redirect URL to JavaScript
       return dict(
           waitpagelink=player.subsession.session.config['waitpagelink']
       )
   pass
   
class TransitionToPracticeTask(Page):
   def vars_for_template(self):
       # Pass transition countdown time to template
       return {
           'transition_time': C.TRANSITION_TIME,
       }

# Define sequence of pages shown to participants
page_sequence = [Welcome, Consent, TaskOverview, TaskInstructionsPage1, TaskInstructionsPage2, RewardStructure, Leaving, Comprehension, PracticeInstructions, WaitPage1, TransitionToPracticeTask]