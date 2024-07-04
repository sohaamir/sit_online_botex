from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'instructions'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 1
    TRANSITION_TIME = 15  # transition time to practice task when players are matched

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    prolific_id = models.StringField(default=str(" "))

# PAGES
class Welcome(Page):
    pass

class Consent(Page):
    @staticmethod              
    def js_vars(player):
        return dict(
            noconsentlink=player.subsession.session.config['noconsentlink']
        )
    pass

class TaskOverview(Page):
    @staticmethod
    def before_next_page(self, timeout_happened):
        self.prolific_id = self.participant.label

class TaskInstructionsPage1(Page):
    pass

class TaskInstructionsPage2(Page):
    pass

class Leaving(Page):
    pass

class Comprehension(Page):
    pass

class PracticeInstructions(Page):
    pass

class WaitPage1(WaitPage):
    template_name = 'instructions/WaitPage1.html'

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

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
    
class TransitionToPracticeTask(Page):
    def vars_for_template(self):
        return {
            'transition_time': C.TRANSITION_TIME,
        }

page_sequence = [Welcome, Consent, TaskOverview, TaskInstructionsPage1, TaskInstructionsPage2, Leaving, Comprehension, PracticeInstructions, WaitPage1, TransitionToPracticeTask]