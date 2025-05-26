# moral_inference/__init__.py

from otree.api import *
import random
import json

author = 'Your Name'

doc = """
Moral Inference Task: Players form expectations about agents' moral character, 
make predictions about agent behavior, and then play trust games with the agents.
"""

class C(BaseConstants):
    NAME_IN_URL = 'moral_inference'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    
    # Agent types
    AGENT_TYPES = ['neutral', 'generous', 'selfish']
    
    # Number of prediction trials
    NEUTRAL_TRIALS = 30
    GENEROUS_TRIALS = 50
    SELFISH_TRIALS = 50
    
    # Belief report frequency (every N trials)
    BELIEF_REPORT_FREQUENCY = 3
    
    # Trust game endowment
    TRUST_ENDOWMENT = 10  # 10 cents
    TRUST_MULTIPLIER = 3
    
    # Scales
    MORAL_SCALE = [
        (1, 'Very Nasty'),
        (2, 'Nasty'),
        (3, 'Somewhat Nasty'),
        (4, 'Neutral'),
        (5, 'Somewhat Nice'),
        (6, 'Nice'),
        (7, 'Very Nice')
    ]
    
    CERTAINTY_SCALE = [
        (1, 'Very Unsure'),
        (2, 'Unsure'),
        (3, 'Somewhat Unsure'),
        (4, 'Neutral'),
        (5, 'Somewhat Sure'),
        (6, 'Sure'),
        (7, 'Very Sure')
    ]

class Subsession(BaseSubsession):
    def creating_session(self):
        for player in self.get_players():
            player.initialize_experiment()

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # Current agent being evaluated
    current_agent = models.StringField()
    current_agent_index = models.IntegerField(initial=0)
    current_trial = models.IntegerField(initial=0)
    
    # Prior beliefs (before prediction phase)
    prior_moral_belief_neutral = models.IntegerField(min=1, max=7)
    prior_certainty_neutral = models.IntegerField(min=1, max=7)
    prior_moral_belief_generous = models.IntegerField(min=1, max=7)
    prior_certainty_generous = models.IntegerField(min=1, max=7)
    prior_moral_belief_selfish = models.IntegerField(min=1, max=7)
    prior_certainty_selfish = models.IntegerField(min=1, max=7)
    
    # Current beliefs during prediction phase (JSON stored)
    current_beliefs = models.LongStringField(initial='{}')
    
    # Prediction phase data (JSON stored)
    prediction_data = models.LongStringField(initial='{}')
    
    # Trust game decisions
    trust_amount_neutral = models.IntegerField(min=0, max=C.TRUST_ENDOWMENT)
    trust_amount_generous = models.IntegerField(min=0, max=C.TRUST_ENDOWMENT)
    trust_amount_selfish = models.IntegerField(min=0, max=C.TRUST_ENDOWMENT)
    
    # Trust game outcomes
    return_amount_neutral = models.FloatField()
    return_amount_generous = models.FloatField()
    return_amount_selfish = models.FloatField()
    
    # Progress tracking
    experiment_phase = models.StringField(initial='instructions')  # instructions, prior_beliefs, prediction, trust_game, complete
    
    def initialize_experiment(self):
        """Initialize the experiment data structures"""
        # Generate agent choice patterns
        self.generate_agent_patterns()
        
        # Initialize current beliefs storage
        beliefs = {
            'neutral': [],
            'generous': [],
            'selfish': []
        }
        self.current_beliefs = json.dumps(beliefs)
        
        # Initialize prediction data storage
        prediction_data = {
            'neutral': {'trials': [], 'completed': False},
            'generous': {'trials': [], 'completed': False},
            'selfish': {'trials': [], 'completed': False}
        }
        self.prediction_data = json.dumps(prediction_data)
    
    def generate_agent_patterns(self):
        """Generate predetermined choice patterns for each agent type"""
        patterns = {}
        
        # Neutral agent: roughly 50/50 between selfish and generous choices
        patterns['neutral'] = self.generate_choice_pattern(C.NEUTRAL_TRIALS, selfish_probability=0.5)
        
        # Generous agent: mostly generous choices (20% selfish)
        patterns['generous'] = self.generate_choice_pattern(C.GENEROUS_TRIALS, selfish_probability=0.2)
        
        # Selfish agent: mostly selfish choices (80% selfish)
        patterns['selfish'] = self.generate_choice_pattern(C.SELFISH_TRIALS, selfish_probability=0.8)
        
        # Store in participant vars
        self.participant.vars['agent_patterns'] = patterns
    
    def generate_choice_pattern(self, num_trials, selfish_probability):
        """Generate a sequence of choices for an agent"""
        trials = []
        for i in range(num_trials):
            # Generate scenario (profit for decider, shocks for receiver)
            decider_profit_option_a = random.randint(5, 15)
            decider_profit_option_b = random.randint(5, 15)
            receiver_shocks_option_a = random.randint(0, 10)
            receiver_shocks_option_b = random.randint(0, 10)
            
            # Determine agent's choice based on their type
            # Agent chooses A if it's more generous (fewer shocks for same/better profit)
            # or if random number < selfish_probability, choose the selfish option
            
            option_a_generosity = decider_profit_option_a - receiver_shocks_option_a
            option_b_generosity = decider_profit_option_b - receiver_shocks_option_b
            
            if random.random() < selfish_probability:
                # Choose more selfish option
                agent_choice = 'A' if option_a_generosity < option_b_generosity else 'B'
            else:
                # Choose more generous option
                agent_choice = 'A' if option_a_generosity > option_b_generosity else 'B'
            
            trials.append({
                'trial': i + 1,
                'decider_profit_a': decider_profit_option_a,
                'decider_profit_b': decider_profit_option_b,
                'receiver_shocks_a': receiver_shocks_option_a,
                'receiver_shocks_b': receiver_shocks_option_b,
                'agent_choice': agent_choice
            })
        
        return trials
    
    def get_current_trial_data(self):
        """Get the current trial data for the current agent"""
        patterns = self.participant.vars.get('agent_patterns', {})
        current_pattern = patterns.get(self.current_agent, [])
        
        if self.current_trial < len(current_pattern):
            return current_pattern[self.current_trial]
        return None
    
    def record_prediction(self, prediction, is_correct):
        """Record a prediction and its accuracy"""
        prediction_data = json.loads(self.prediction_data)
        
        trial_data = self.get_current_trial_data()
        if trial_data:
            trial_record = {
                'trial': self.current_trial + 1,
                'prediction': prediction,
                'correct_answer': trial_data['agent_choice'],
                'is_correct': is_correct,
                'decider_profit_a': trial_data['decider_profit_a'],
                'decider_profit_b': trial_data['decider_profit_b'],
                'receiver_shocks_a': trial_data['receiver_shocks_a'],
                'receiver_shocks_b': trial_data['receiver_shocks_b']
            }
            
            prediction_data[self.current_agent]['trials'].append(trial_record)
            self.prediction_data = json.dumps(prediction_data)
    
    def record_belief_update(self, moral_belief, certainty):
        """Record updated beliefs during prediction phase"""
        beliefs = json.loads(self.current_beliefs)
        
        belief_record = {
            'trial': self.current_trial + 1,
            'moral_belief': moral_belief,
            'certainty': certainty
        }
        
        beliefs[self.current_agent].append(belief_record)
        self.current_beliefs = json.dumps(beliefs)
    
    def calculate_trust_return(self, agent_type, trust_amount):
        """Calculate how much the agent returns in the trust game"""
        multiplied_amount = trust_amount * C.TRUST_MULTIPLIER
        
        # Different return rates based on agent type
        if agent_type == 'generous':
            return_rate = random.uniform(0.7, 0.9)  # Returns 70-90%
        elif agent_type == 'selfish':
            return_rate = random.uniform(0.1, 0.3)  # Returns 10-30%
        else:  # neutral
            return_rate = random.uniform(0.4, 0.6)  # Returns 40-60%
        
        return multiplied_amount * return_rate

# PAGES

class Instructions(Page):
    @staticmethod
    def is_displayed(player):
        return player.experiment_phase == 'instructions'
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.experiment_phase = 'prior_beliefs'
        player.current_agent = 'neutral'

class PriorBeliefs(Page):
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        agent = player.current_agent
        return [f'prior_moral_belief_{agent}', f'prior_certainty_{agent}']
    
    @staticmethod
    def is_displayed(player):
        return player.experiment_phase == 'prior_beliefs'
    
    @staticmethod
    def vars_for_template(player):
        return {
            'agent_type': player.current_agent.title(),
            'moral_scale': C.MORAL_SCALE,
            'certainty_scale': C.CERTAINTY_SCALE
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.experiment_phase = 'prediction'
        player.current_trial = 0

class PredictionTrial(Page):
    form_model = 'player'
    form_fields = ['prediction_choice']
    
    @staticmethod
    def is_displayed(player):
        return (player.experiment_phase == 'prediction' and 
                player.get_current_trial_data() is not None)
    
    @staticmethod
    def vars_for_template(player):
        trial_data = player.get_current_trial_data()
        if trial_data:
            return {
                'agent_type': player.current_agent.title(),
                'trial_number': player.current_trial + 1,
                'decider_profit_a': trial_data['decider_profit_a'],
                'decider_profit_b': trial_data['decider_profit_b'],
                'receiver_shocks_a': trial_data['receiver_shocks_a'],
                'receiver_shocks_b': trial_data['receiver_shocks_b']
            }
        return {}
    
    prediction_choice = models.StringField(
        choices=[('A', 'Option A'), ('B', 'Option B')],
        widget=widgets.RadioSelect
    )
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        trial_data = player.get_current_trial_data()
        if trial_data:
            is_correct = player.prediction_choice == trial_data['agent_choice']
            player.record_prediction(player.prediction_choice, is_correct)
            player.current_trial += 1

class PredictionFeedback(Page):
    @staticmethod
    def is_displayed(player):
        return (player.experiment_phase == 'prediction' and 
                player.current_trial > 0)
    
    @staticmethod
    def vars_for_template(player):
        prediction_data = json.loads(player.prediction_data)
        trials = prediction_data[player.current_agent]['trials']
        
        if trials:
            last_trial = trials[-1]
            return {
                'agent_type': player.current_agent.title(),
                'trial_number': last_trial['trial'],
                'your_prediction': last_trial['prediction'],
                'correct_answer': last_trial['correct_answer'],
                'is_correct': last_trial['is_correct'],
                'decider_profit_a': last_trial['decider_profit_a'],
                'decider_profit_b': last_trial['decider_profit_b'],
                'receiver_shocks_a': last_trial['receiver_shocks_a'],
                'receiver_shocks_b': last_trial['receiver_shocks_b']
            }
        return {}
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Check if we need to show belief update
        if player.current_trial % C.BELIEF_REPORT_FREQUENCY == 0:
            pass  # Will go to BeliefUpdate page
        elif player.get_current_trial_data() is None:
            # No more trials for this agent
            player.experiment_phase = 'trust_game'

class BeliefUpdate(Page):
    form_model = 'player'
    form_fields = ['current_moral_belief', 'current_certainty']
    
    current_moral_belief = models.IntegerField(
        min=1, max=7,
        widget=widgets.RadioSelectHorizontal,
        choices=C.MORAL_SCALE
    )
    current_certainty = models.IntegerField(
        min=1, max=7,
        widget=widgets.RadioSelectHorizontal,
        choices=C.CERTAINTY_SCALE
    )
    
    @staticmethod
    def is_displayed(player):
        return (player.experiment_phase == 'prediction' and 
                player.current_trial % C.BELIEF_REPORT_FREQUENCY == 0 and
                player.current_trial > 0 and
                player.get_current_trial_data() is not None)
    
    @staticmethod
    def vars_for_template(player):
        return {
            'agent_type': player.current_agent.title(),
            'trial_number': player.current_trial,
            'moral_scale': C.MORAL_SCALE,
            'certainty_scale': C.CERTAINTY_SCALE
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.record_belief_update(player.current_moral_belief, player.current_certainty)
        
        # Check if prediction phase is complete
        if player.get_current_trial_data() is None:
            player.experiment_phase = 'trust_game'

class TrustGame(Page):
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        return [f'trust_amount_{player.current_agent}']
    
    @staticmethod
    def is_displayed(player):
        return player.experiment_phase == 'trust_game'
    
    @staticmethod
    def vars_for_template(player):
        return {
            'agent_type': player.current_agent.title(),
            'endowment': C.TRUST_ENDOWMENT,
            'multiplier': C.TRUST_MULTIPLIER
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Calculate agent's return
        trust_amount = getattr(player, f'trust_amount_{player.current_agent}')
        return_amount = player.calculate_trust_return(player.current_agent, trust_amount)
        setattr(player, f'return_amount_{player.current_agent}', return_amount)
        
        # Move to next agent or complete experiment
        player.current_agent_index += 1
        
        if player.current_agent_index < len(C.AGENT_TYPES):
            # Move to next agent
            player.current_agent = C.AGENT_TYPES[player.current_agent_index]
            player.experiment_phase = 'prior_beliefs'
            player.current_trial = 0
        else:
            # Experiment complete
            player.experiment_phase = 'complete'

class TrustGameResults(Page):
    @staticmethod
    def is_displayed(player):
        return (player.experiment_phase == 'complete' or 
                (player.experiment_phase == 'prior_beliefs' and player.current_agent_index > 0))
    
    @staticmethod
    def vars_for_template(player):
        # Show results for the previous agent
        if player.current_agent_index > 0:
            prev_agent = C.AGENT_TYPES[player.current_agent_index - 1]
        else:
            prev_agent = 'selfish'  # Last agent when experiment is complete
        
        trust_amount = getattr(player, f'trust_amount_{prev_agent}')
        return_amount = getattr(player, f'return_amount_{prev_agent}')
        final_amount = C.TRUST_ENDOWMENT - trust_amount + return_amount
        
        return {
            'agent_type': prev_agent.title(),
            'trust_amount': trust_amount,
            'multiplied_amount': trust_amount * C.TRUST_MULTIPLIER,
            'return_amount': return_amount,
            'final_amount': final_amount,
            'experiment_complete': player.experiment_phase == 'complete'
        }

class FinalResults(Page):
    @staticmethod
    def is_displayed(player):
        return player.experiment_phase == 'complete'
    
    @staticmethod
    def vars_for_template(player):
        results = {}
        total_earnings = 0
        
        for agent in C.AGENT_TYPES:
            trust_amount = getattr(player, f'trust_amount_{agent}')
            return_amount = getattr(player, f'return_amount_{agent}')
            final_amount = C.TRUST_ENDOWMENT - trust_amount + return_amount
            
            results[agent] = {
                'trust_amount': trust_amount,
                'return_amount': return_amount,
                'final_amount': final_amount
            }
            total_earnings += final_amount
        
        return {
            'results': results,
            'total_earnings': total_earnings
        }

page_sequence = [
    Instructions,
    PriorBeliefs,
    PredictionTrial,
    PredictionFeedback,
    BeliefUpdate,
    TrustGame,
    TrustGameResults,
    FinalResults
]