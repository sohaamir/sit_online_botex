from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'waiting_room'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1
    TRANSITION_TIME = 15  # 15 seconds

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

# PAGES
class WaitPage2(WaitPage):
    template_name = 'waiting_room/WaitPage2.html'

    group_by_arrival_time = True

    @staticmethod
    def vars_for_template(player):
        return {
            'title_text': 'Waiting for Other Players',
        }
    
    @staticmethod              
    def js_vars(player):
        return dict(
            waitpagelink=player.subsession.session.config['waitpagelink']
        )
    pass

class TransitionToMainTask(Page):
    def vars_for_template(self):
        return {
            'transition_time': C.TRANSITION_TIME,
        }

page_sequence = [WaitPage2, TransitionToMainTask]