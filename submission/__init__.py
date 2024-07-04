from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'submission'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

def creating_session(subsession):
    for p in subsession.get_players():
        p.participant.finished = False

# PAGES
class Submission(Page):
    @staticmethod              
    def js_vars(player):
        return dict(
            completionlink=player.subsession.session.config['completionlink']
        )
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.finished = True

page_sequence = [Submission]