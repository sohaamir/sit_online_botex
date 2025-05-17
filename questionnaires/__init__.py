from otree.api import *

author = 'Aamir Sohail'

doc = """
Psychological Questionnaires Battery including LSAS, DASS, AQ-10, AMI, SRP-SF, and SSMS
"""

class C(BaseConstants):
    NAME_IN_URL = 'questionnaires'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    
    # Number of questions in each questionnaire
    NUM_LSAS_QUESTIONS = 24  # Each question has two parts (anxiety and avoidance)
    NUM_DASS_QUESTIONS = 21
    NUM_AQ_QUESTIONS = 10
    NUM_AMI_QUESTIONS = 20
    NUM_SRPSF_QUESTIONS = 29
    NUM_SSMS_QUESTIONS = 21


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Fields for LSAS (Liebowitz Social Anxiety Scale)
    # Each question has two components: anxiety and avoidance
    # Anxiety scores: 0 (None) to 3 (Severe)
    # Avoidance scores: 0 (Never) to 3 (Usually)
    
    # Generate LSAS anxiety fields
    for i in range(1, C.NUM_LSAS_QUESTIONS + 1):
        locals()[f'lsas_anxiety_{i}'] = models.IntegerField(
            choices=[
                [0, 'None'],
                [1, 'Mild'],
                [2, 'Moderate'],
                [3, 'Severe'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Generate LSAS avoidance fields
    for i in range(1, C.NUM_LSAS_QUESTIONS + 1):
        locals()[f'lsas_avoidance_{i}'] = models.IntegerField(
            choices=[
                [0, 'Never (0%)'],
                [1, 'Occasionally (1-33%)'],
                [2, 'Often (34-66%)'],
                [3, 'Usually (67-100%)'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Total scores for LSAS
    lsas_anxiety_score = models.IntegerField()
    lsas_avoidance_score = models.IntegerField()
    lsas_total_score = models.IntegerField()
    
    # LSAS Subscales
    lsas_p_score = models.IntegerField()  # Performance anxiety
    lsas_s_score = models.IntegerField()  # Social interaction anxiety
    
    # Fields for DASS (Depression Anxiety Stress Scale)
    # Each item is scored from 0 (Did not apply to me at all) to 3 (Applied to me very much)
    for i in range(1, C.NUM_DASS_QUESTIONS + 1):
        locals()[f'dass_{i}'] = models.IntegerField(
            choices=[
                [0, 'Did not apply to me at all'],
                [1, 'Applied to me to some degree, or some of the time'],
                [2, 'Applied to me to a considerable degree, or a good part of time'],
                [3, 'Applied to me very much, or most of the time'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Total scores for DASS
    dass_depression_score = models.IntegerField()  # Doubled scores
    dass_anxiety_score = models.IntegerField()     # Doubled scores
    dass_stress_score = models.IntegerField()      # Doubled scores
    dass_total_score = models.IntegerField()
    
    # Fields for AQ-10 (Autism Quotient-10)
    # Scoring is variable according to the question (some are reverse scored)
    for i in range(1, C.NUM_AQ_QUESTIONS + 1):
        locals()[f'aq_{i}'] = models.IntegerField(
            choices=[
                [1, 'Definitely Agree'],
                [2, 'Slightly Agree'],
                [3, 'Slightly Disagree'],
                [4, 'Definitely Disagree'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Attention check questions for AQ-10
    aq_check_1 = models.IntegerField(
        choices=[
            [1, 'Definitely Agree'],
            [2, 'Slightly Agree'],
            [3, 'Slightly Disagree'],
            [4, 'Definitely Disagree'],
        ],
        widget=widgets.RadioSelect,
        label="Please select 'Definitely Disagree' for this question."
    )
    
    aq_check_2 = models.IntegerField(
        choices=[
            [1, 'Definitely Agree'],
            [2, 'Slightly Agree'],
            [3, 'Slightly Disagree'],
            [4, 'Definitely Disagree'],
        ],
        widget=widgets.RadioSelect,
        label="Please select 'Definitely Agree' for this question."
    )
    
    aq_check_3 = models.IntegerField(
        choices=[
            [1, 'Definitely Agree'],
            [2, 'Slightly Agree'],
            [3, 'Slightly Disagree'],
            [4, 'Definitely Disagree'],
        ],
        widget=widgets.RadioSelect,
        label="Please select 'Slightly Agree' for this question."
    )
    
    # Total score for AQ-10
    aq_total_score = models.IntegerField()
    
    # Fields for AMI (Ambivalent Misogyny Inventory)
    # Scored from 4 (Completely Untrue) to 0 (Completely True)
    for i in range(1, C.NUM_AMI_QUESTIONS + 1):
        locals()[f'ami_{i}'] = models.IntegerField(
            choices=[
                [4, 'Completely Untrue'],
                [3, 'Somewhat Untrue'],
                [2, 'Neither True nor Untrue'],
                [1, 'Somewhat True'],
                [0, 'Completely True'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Total score for AMI
    ami_total_score = models.IntegerField()
    
    # AMI Subscales
    ami_es_score = models.IntegerField()  # Emotional Stereotyping subscale
    ami_sm_score = models.IntegerField()  # Sexual Manipulation subscale
    ami_ba_score = models.IntegerField()  # Benevolent Acts subscale
    
    # Fields for SRP-SF (Self-Report Psychopathy Scale-Short Form)
    # Scored from 1 (Disagree Strongly) to 5 (Agree Strongly)
    # With one reverse-scored item
    for i in range(1, C.NUM_SRPSF_QUESTIONS + 1):
        locals()[f'srpsf_{i}'] = models.IntegerField(
            choices=[
                [1, 'Disagree Strongly'],
                [2, 'Disagree'],
                [3, 'Neutral'],
                [4, 'Agree'],
                [5, 'Agree Strongly'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Total score for SRP-SF
    srpsf_total_score = models.IntegerField()
    
    # SRP-SF Subscales
    srpsf_ipm_score = models.IntegerField()  # Interpersonal Manipulation
    srpsf_ca_score = models.IntegerField()   # Callous Affect
    srpsf_els_score = models.IntegerField()  # Erratic Lifestyle
    srpsf_ct_score = models.IntegerField()   # Criminal Tendencies
    
    # Fields for SSMS (Schizotypal Symptoms & Mood Scale)
    # Binary Yes/No answers with variable scoring
    for i in range(1, C.NUM_SSMS_QUESTIONS + 1):
        locals()[f'ssms_{i}'] = models.IntegerField(
            choices=[
                [0, 'No'],
                [1, 'Yes'],
            ],
            widget=widgets.RadioSelect,
            label=f"Question {i}"
        )
    del i  # Delete the loop variable
    
    # Total score for SSMS
    ssms_total_score = models.IntegerField()
    
    # SSMS Subscales
    ssms_cd_score = models.IntegerField()  # Cognitive Disorganization
    ssms_ia_score = models.IntegerField()  # Introvertive Anhedonia
    

    # Calculate LSAS scores
    def calculate_lsas_scores(self):
        # Calculate main scores
        anxiety_score = sum(getattr(self, f'lsas_anxiety_{i}') for i in range(1, C.NUM_LSAS_QUESTIONS + 1))
        avoidance_score = sum(getattr(self, f'lsas_avoidance_{i}') for i in range(1, C.NUM_LSAS_QUESTIONS + 1))
        self.lsas_anxiety_score = anxiety_score
        self.lsas_avoidance_score = avoidance_score
        self.lsas_total_score = anxiety_score + avoidance_score
        
        # Calculate LSAS-P subscale (Performance anxiety)
        # Questions 1, 2, 3, 4, 6, 8, 9, 13, 14, 16, 17, 20, 21
        lsas_p_questions = [1, 2, 3, 4, 6, 8, 9, 13, 14, 16, 17, 20, 21]
        lsas_p_anxiety = sum(getattr(self, f'lsas_anxiety_{i}') for i in lsas_p_questions)
        lsas_p_avoidance = sum(getattr(self, f'lsas_avoidance_{i}') for i in lsas_p_questions)
        self.lsas_p_score = lsas_p_anxiety + lsas_p_avoidance
        
        # Calculate LSAS-S subscale (Social interaction anxiety)
        # Questions 5, 7, 10, 11, 12, 15, 18, 19, 22, 23, 24
        lsas_s_questions = [5, 7, 10, 11, 12, 15, 18, 19, 22, 23, 24]
        lsas_s_anxiety = sum(getattr(self, f'lsas_anxiety_{i}') for i in lsas_s_questions)
        lsas_s_avoidance = sum(getattr(self, f'lsas_avoidance_{i}') for i in lsas_s_questions)
        self.lsas_s_score = lsas_s_anxiety + lsas_s_avoidance
    
    # Calculate DASS scores
    def calculate_dass_scores(self):
        # Depression items: 3, 5, 10, 13, 16, 17, 21
        depression_items = [3, 5, 10, 13, 16, 17, 21]
        # Anxiety items: 2, 4, 7, 9, 15, 19, 20
        anxiety_items = [2, 4, 7, 9, 15, 19, 20]
        # Stress items: 1, 6, 8, 11, 12, 14, 18
        stress_items = [1, 6, 8, 11, 12, 14, 18]
        
        # Double the scores for each subscale as per instructions
        depression_score = sum(getattr(self, f'dass_{i}') for i in depression_items) * 2
        anxiety_score = sum(getattr(self, f'dass_{i}') for i in anxiety_items) * 2
        stress_score = sum(getattr(self, f'dass_{i}') for i in stress_items) * 2
        
        self.dass_depression_score = depression_score
        self.dass_anxiety_score = anxiety_score
        self.dass_stress_score = stress_score
        self.dass_total_score = depression_score + anxiety_score + stress_score
    
    # Calculate AQ-10 scores
    def calculate_aq_scores(self):
        # Questions where "agree" (1 or 2) is scored as 1 point
        agree_scored = [1, 7, 8, 10]
        # Questions where "disagree" (3 or 4) is scored as 1 point
        disagree_scored = [2, 3, 4, 5, 6, 9]
        
        score = 0
        for i in agree_scored:
            if getattr(self, f'aq_{i}') in [1, 2]:  # Definitely or Slightly Agree
                score += 1
                
        for i in disagree_scored:
            if getattr(self, f'aq_{i}') in [3, 4]:  # Slightly or Definitely Disagree
                score += 1
                
        self.aq_total_score = score
    
    # Calculate AMI scores
    def calculate_ami_score(self):
        # Total score
        self.ami_total_score = sum(getattr(self, f'ami_{i}') for i in range(1, C.NUM_AMI_QUESTIONS + 1))
        
        # AMI-ES (Emotional Stereotyping) - questions 1, 6, 7, 13, 16, 18
        ami_es_items = [1, 6, 7, 13, 16, 18]
        self.ami_es_score = sum(getattr(self, f'ami_{i}') for i in ami_es_items)
        
        # AMI-SM (Sexual Manipulation) - questions 2, 3, 4, 8, 14, 17
        ami_sm_items = [2, 3, 4, 8, 14, 17]
        self.ami_sm_score = sum(getattr(self, f'ami_{i}') for i in ami_sm_items)
        
        # AMI-BA (Benevolent Acts) - questions 5, 9, 10, 11, 12, 15
        ami_ba_items = [5, 9, 10, 11, 12, 15]
        self.ami_ba_score = sum(getattr(self, f'ami_{i}') for i in ami_ba_items)
    
    # Calculate SRP-SF scores
    def calculate_srpsf_score(self):
        # Get all standard scores except item 2 (changed from 19)
        all_items_except_2 = list(range(1, C.NUM_SRPSF_QUESTIONS + 1))
        all_items_except_2.remove(2)  # Changed from 19
        standard_score = sum(getattr(self, f'srpsf_{i}') for i in all_items_except_2)
        
        # Handle reverse-scored item 2 (changed from 19)
        reverse_score = 6 - getattr(self, 'srpsf_2')  # Changed from srpsf_19
        
        self.srpsf_total_score = standard_score + reverse_score
        
        # SRPSF-IPM (Interpersonal Manipulation) - questions 7, 9, 10, 15, 19, 23, 26
        # No change needed here if 19 is not reverse-scored in this subscale
        srpsf_ipm_items = [7, 9, 10, 15, 19, 23, 26]
        self.srpsf_ipm_score = sum(getattr(self, f'srpsf_{i}') for i in srpsf_ipm_items)
        
        # SRPSF-CA (Callous Affect) - questions 3, 8, 13, 16, 18, 24, 28
        srpsf_ca_items = [3, 8, 13, 16, 18, 24, 28]
        self.srpsf_ca_score = sum(getattr(self, f'srpsf_{i}') for i in srpsf_ca_items)
        
        # SRPSF-ELS (Erratic Lifestyle) - questions 1, 4, 11, 14, 17, 21, 27
        srpsf_els_items = [1, 4, 11, 14, 17, 21, 27]
        self.srpsf_els_score = sum(getattr(self, f'srpsf_{i}') for i in srpsf_els_items)
        
        # SRPSF-CT (Criminal Tendencies) - questions 2, 5, 6, 12, 22, 25, 29
        # Need to handle reverse-scored item 2 here
        srpsf_ct_items = [5, 6, 12, 22, 25, 29]  # Removed item 2 from direct sum
        ct_score = sum(getattr(self, f'srpsf_{i}') for i in srpsf_ct_items) + (6 - getattr(self, 'srpsf_2'))
        self.srpsf_ct_score = ct_score
    
    # Calculate SSMS scores
    def calculate_ssms_score(self):
        # Questions where Yes=1, No=0
        yes_scored = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17, 20, 21]
        # Questions where Yes=0, No=1 (reverse scored)
        no_scored = [14, 15, 16, 18, 19]
        
        score = 0
        for i in yes_scored:
            score += getattr(self, f'ssms_{i}')
            
        for i in no_scored:
            score += (1 - getattr(self, f'ssms_{i}'))
            
        self.ssms_total_score = score
        
        # SSMS-CD (Cognitive Disorganization) - questions 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
        ssms_cd_items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        # All CD items are yes-scored
        self.ssms_cd_score = sum(getattr(self, f'ssms_{i}') for i in ssms_cd_items)
        
        # SSMS-IA (Introvertive Anhedonia)
        ssms_ia_yes_scored = [12, 13, 17, 20, 21]  
        ssms_ia_no_scored = [14, 15, 16, 18, 19]
        
        ia_score = 0
        for i in ssms_ia_yes_scored:
            ia_score += getattr(self, f'ssms_{i}')
        for i in ssms_ia_no_scored:
            ia_score += (1 - getattr(self, f'ssms_{i}'))
            
        self.ssms_ia_score = ia_score


# PAGES
class Instructions(Page):
    """General instructions for the questionnaire battery"""
    pass

class LSAS(Page):
    """Liebowitz Social Anxiety Scale"""
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        anxiety_fields = [f'lsas_anxiety_{i}' for i in range(1, C.NUM_LSAS_QUESTIONS + 1)]
        avoidance_fields = [f'lsas_avoidance_{i}' for i in range(1, C.NUM_LSAS_QUESTIONS + 1)]
        return anxiety_fields + avoidance_fields
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.calculate_lsas_scores()

class DASS(Page):
    """Depression Anxiety Stress Scale"""
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        return [f'dass_{i}' for i in range(1, C.NUM_DASS_QUESTIONS + 1)]
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.calculate_dass_scores()

class AQ(Page):
    """Autism Quotient-10"""
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        aq_fields = [f'aq_{i}' for i in range(1, C.NUM_AQ_QUESTIONS + 1)]
        check_fields = ['aq_check_1', 'aq_check_2', 'aq_check_3']
        return aq_fields + check_fields
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.calculate_aq_scores()

class AMI(Page):
    """Ambivalent Misogyny Inventory"""
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        return [f'ami_{i}' for i in range(1, C.NUM_AMI_QUESTIONS + 1)]
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.calculate_ami_score()

class SRPSF(Page):
    """Self-Report Psychopathy Scale-Short Form"""
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        return [f'srpsf_{i}' for i in range(1, C.NUM_SRPSF_QUESTIONS + 1)]
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.calculate_srpsf_score()

class SSMS(Page):
    """Schizotypal Symptoms & Mood Scale"""
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        return [f'ssms_{i}' for i in range(1, C.NUM_SSMS_QUESTIONS + 1)]
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.calculate_ssms_score()

page_sequence = [
    Instructions,
    LSAS,
    DASS,
    AQ,
    AMI,
    SRPSF,
    SSMS
]