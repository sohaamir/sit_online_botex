from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'instructions'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

# PAGES
class WaitPage1(WaitPage):
    pass

class Welcome(Page):
    pass

class Consent(Page):
    pass

class TaskOverviewPage1(Page):
    pass

class TaskOverviewPage2(Page):
    pass

class TaskInstructionsPage1(Page):
    pass

class TaskInstructionsPage2(Page):
    pass

class Comprehension(Page):
    pass

class PracticeInstructions(Page):
    pass

class WaitPage2(WaitPage):
    template_name = 'instructions/WaitPage2.html'

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        waiting_players = C.PLAYERS_PER_GROUP - len(group.get_players())
        return dict(
            waiting_players=waiting_players,
            title_text="Waiting for other players",
        )

page_sequence = [WaitPage1, Welcome, Consent, TaskOverviewPage1, TaskOverviewPage2, TaskInstructionsPage1, TaskInstructionsPage2, Comprehension, PracticeInstructions, WaitPage2]