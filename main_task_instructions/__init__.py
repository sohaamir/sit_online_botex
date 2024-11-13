from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'main_task_instructions'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    def creating_session(self):
        # Break up existing groups
        self.group_randomly(fixed_id_in_group=False)

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

# PAGES
class MainTaskInstructions(Page):
    pass

page_sequence = [MainTaskInstructions]