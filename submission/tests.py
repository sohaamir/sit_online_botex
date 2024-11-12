from otree.api import Bot, expect
from . import *
import random

class PlayerBot(Bot):
    def play_round(self):
        # Simulate completing the feedback form
        yield Feedback, {
            'task_understanding': random.randint(0, 100),
            'engagement': random.randint(0, 100),
            'influence': random.randint(0, 100),
            'real_players': random.randint(0, 100),
            'attention_focus': random.randint(0, 100)
        }
        
        # Check if completionlink is defined in session config
        assert 'completionlink' in self.session.config, "completionlink not found in session config"
        
        # Simulate final submission
        yield Submit
        
    def validate_play(self):
        """Validate that all required fields were completed"""
        # Check that all survey fields have valid values
        expect(0 <= self.player.task_understanding <= 100)
        expect(0 <= self.player.engagement <= 100)
        expect(0 <= self.player.influence <= 100)
        expect(0 <= self.player.real_players <= 100)
        expect(0 <= self.player.attention_focus <= 100)
        
        # Verify participant is marked as finished
        expect(self.player.participant.finished, True)
        
        # Check if prolific_id was properly carried through
        expect(hasattr(self.player.participant.vars, 'prolific_id'))