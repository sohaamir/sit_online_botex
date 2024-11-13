from otree.api import *

# Constants class defining game-wide settings
class C(BaseConstants):
  NAME_IN_URL = 'waiting_room'  # URL segment for waiting room
  PLAYERS_PER_GROUP = None      # Set to None when using group_by_arrival_time
  NUM_ROUNDS = 1                # Single round game
  TRANSITION_TIME = 15          # Seconds before transition to main task

# Model classes 
class Subsession(BaseSubsession):
   def group_by_arrival_time_method(self, waiting_players):
       # Form groups of 5 players when available
       if len(waiting_players) >= 5:
           return waiting_players[:5]
       return None

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

  @staticmethod
  def after_all_players_arrive(group: Group):
       # This runs after a group is formed
       # Store each player's group assignment and position
    for p in group.subsession.get_players():
        p.participant.vars['main_task_group'] = p.group.id_in_subsession
        p.participant.vars['main_task_id_in_group'] = p.id_in_group

class TransitionToMainTask(Page):
  def vars_for_template(self):
      # Pass transition countdown time to template
      return {
          'transition_time': C.TRANSITION_TIME,
      }

# Define sequence of pages shown to participants
page_sequence = [WaitPage2, TransitionToMainTask]