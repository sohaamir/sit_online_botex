from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'submission'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    task_understanding = models.IntegerField(min=0, max=100)
    engagement = models.IntegerField(min=0, max=100)
    influence = models.IntegerField(min=0, max=100)
    real_players = models.IntegerField(min=0, max=100)
    attention_focus = models.IntegerField(min=0, max=100)

    def get_prolific_id(self):
        return self.participant.vars.get('prolific_id', '')

def creating_session(subsession):
    for p in subsession.get_players():
        p.participant.finished = False

# PAGES
class Feedback(Page):
    form_model = 'player'
    form_fields = ['task_understanding', 'engagement', 'influence', 'real_players', 'attention_focus']

class Submit(Page):
    @staticmethod
    def js_vars(player):
        return dict(
            completionlink=player.session.config['completionlink']
        )
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.finished = True

    @staticmethod
    def vars_for_template(player):
        return {
            'prolific_id': player.get_prolific_id()
        }

page_sequence = [Feedback, Submit]