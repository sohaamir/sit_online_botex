from otree.api import Bot, expect
from . import *

class PlayerBot(Bot):
    def play_round(self):
        # Test the sequence of instruction pages
        yield Welcome
        yield Consent
        yield TaskOverview
        
        # Check if Prolific ID is stored
        expect(self.player.prolific_id, 'No ID provided')
        
        yield TaskInstructionsPage1
        yield TaskInstructionsPage2
        yield RewardStructure
        yield Leaving
        yield Comprehension
        yield AdjustDimensions
        yield FixDimensions
        yield PracticeInstructions
        yield WaitPage1
        yield TransitionToPracticeTask