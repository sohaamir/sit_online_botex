from otree.api import *

# Constants class defining game-wide settings
class C(BaseConstants):
   NAME_IN_URL = 'waiting_room'  # URL segment for waiting room
   PLAYERS_PER_GROUP = 5         # Number of players needed to form group
   NUM_ROUNDS = 1                # Single round game
   TRANSITION_TIME = 15          # Seconds before transition to main task

# Model classes 
class Subsession(BaseSubsession):
   pass  # No subsession-level data needed

class Group(BaseGroup):
   pass  # No group-level data needed

class Player(BasePlayer):
   pass  # No player-level data needed

# Page classes
class WaitPage2(WaitPage):
   template_name = 'waiting_room/WaitPage2.html'  # Custom wait page template

   group_by_arrival_time = True  # Form groups as players arrive

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

class TransitionToMainTask(Page):
   def vars_for_template(self):
       # Pass transition countdown time to template
       return {
           'transition_time': C.TRANSITION_TIME,
       }

# Define sequence of pages
page_sequence = [WaitPage2, TransitionToMainTask]