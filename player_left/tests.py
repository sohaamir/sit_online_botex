from otree.api import Bot
from . import *

class PlayerBot(Bot):
    def play_round(self):
        # Check if playerleftlink is defined in session config
        assert 'playerleftlink' in self.session.config, "playerleftlink not found in session config"
        
        # Simulate viewing the PlayerLeft page
        yield PlayerBot
        
        def validate_play(self):
            # Verify the page was shown
            expect(self.player.participant._index_in_pages, 1)