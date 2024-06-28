from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'player_left'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

# PAGES
class PlayerLeft(Page):
    
    @staticmethod              
    def js_vars(player):
        return dict(
            completionlink=
              player.subsession.session.config['completionlink']
        )
    pass

page_sequence = [PlayerLeft]