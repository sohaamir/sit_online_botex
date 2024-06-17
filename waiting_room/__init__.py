from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'waiting_room'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

# PAGES
class MainTaskInstructions(Page):
    pass

class WaitPage3(WaitPage):
    pass

page_sequence = [MainTaskInstructions, WaitPage3]