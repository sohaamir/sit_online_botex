def generate_trial_sequence():
    # Using a fixed random seed ensures the same sequence is generated each time the experiment runs
    # This is important for reproducibility and consistency across different groups
    random.seed(40)  # You can change this number, but keep it constant

    sequence = []
    # Randomly select which image will start as the high-probability option
    current_image = random.choice(['option1A.bmp', 'option1B.bmp'])
    reversal_rounds = []
    
    # Create a list of rounds where reversals will occur
    # Reversals happen every 9-11 rounds (randomly determined)
    current_round = random.randint(9, 11)
    while current_round <= NUM_ROUNDS:
        reversal_rounds.append(current_round)
        current_round += random.randint(9, 11)
    
    # Generate the full sequence of trials
    # At each reversal round, the high-probability image switches
    for round_number in range(1, NUM_ROUNDS + 1):
        if round_number in reversal_rounds:
            current_image = 'option1B.bmp' if current_image == 'option1A.bmp' else 'option1A.bmp'
        sequence.append((round_number, current_image))

    # Save sequence to CSV
    file_path = os.path.join(os.getcwd(), 'reversal_sequence.csv')
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['round', 'seventy_percent_image', 'is_reversal'])
        for round_num, image in sequence:
            writer.writerows([(round_num, image, round_num in reversal_rounds)])

    print(f"Reversal rounds: {reversal_rounds}")
    return sequence, reversal_rounds

# -------------------------------------------------------------------------------------------------------------------- #
# ---- REWARD SEQUENCE: GENERATE A SEQUENCE OF REWARDS FOR THE EXPERIMENT BASED ON THE NUMBER OF ROUNDS ------ #

# Define the core parameters of the experiment
NUM_ROUNDS = 60  # Total number of rounds in the experiment
REWARD_PROBABILITY_A = 0.75  # 75% chance of reward for option A when it's the high-probability option
REWARD_PROBABILITY_B = 0.25  # 25% chance of reward for option A when it's the low-probability option
DECISION_TIME = 3.0 # Time limit for making choices and bets (3 seconds)

# This function generates the actual sequence of rewards that players will receive
# It ensures a balanced distribution of rewards while maintaining the intended probabilities
def generate_reward_sequence(num_rounds, reversal_rounds):
    sequence = []
    current_high_prob_image = 'A'  # Start with image A as high probability
    high_prob_rewards = 0  # Counter for high probability rewards given
    low_prob_rewards = 0   # Counter for low probability rewards given
    target_high_rewards = 45  # Target number of high probability rewards (75% of 60 rounds)
    target_low_rewards = 15   # Target number of low probability rewards (25% of 60 rounds)

    # Prepare CSV file headers for logging the reward sequence
    csv_data = [['Round', 'High Prob', 'reward_A', 'reward_B']]

    print("\nGenerated Reward Sequence:")
    print("Round | High Prob | reward_A | reward_B")
    print("------|-----------|----------|----------")

    # Helper function to prevent too many consecutive high probability rewards
    def can_add_high_prob():
        if len(sequence) < 3:
            return True
        return not all(s[0] if current_high_prob_image == 'A' else s[1] for s in sequence[-3:])

    # Helper function to prevent too many consecutive low probability rewards
    def can_add_low_prob():
        if len(sequence) < 3:
            return True
        return not all(s[1] if current_high_prob_image == 'A' else s[0] for s in sequence[-3:])

    # Generate rewards for each round
    for round_num in range(1, num_rounds + 1):
        # Switch the high probability image at reversal rounds
        if round_num in reversal_rounds:
            current_high_prob_image = 'B' if current_high_prob_image == 'A' else 'A'
            print("-------|-----------|----------|----------")
            csv_data.append(['-------|-----------|----------|----------'])

        # Calculate how many more rewards are needed of each type
        remaining_rounds = num_rounds - round_num + 1
        min_high_needed = target_high_rewards - high_prob_rewards
        min_low_needed = target_low_rewards - low_prob_rewards

        # Logic to ensure we meet our target numbers while maintaining randomness
        if min_high_needed > remaining_rounds * 0.7:
            choice = 'high'
        elif min_low_needed > remaining_rounds * 0.3:
            choice = 'low'
        elif not can_add_high_prob():
            choice = 'low'
        elif not can_add_low_prob():
            choice = 'high'
        else:
            choice = random.choices(['high', 'low'], weights=[0.7, 0.3])[0]

        # Assign rewards based on the choice
        if choice == 'high' and can_add_high_prob():
            reward_A, reward_B = (1, 0) if current_high_prob_image == 'A' else (0, 1)
            high_prob_rewards += 1
        else:
            reward_A, reward_B = (0, 1) if current_high_prob_image == 'A' else (1, 0)
            low_prob_rewards += 1

        sequence.append((reward_A, reward_B))
        print(f"{round_num:5d} | {current_high_prob_image:9s} | {reward_A:8d} | {reward_B:8d}")
        csv_data.append([round_num, current_high_prob_image, reward_A, reward_B])

    # Calculate and display statistics about the generated sequence
    high_prob_percentage = (high_prob_rewards / num_rounds) * 100
    low_prob_percentage = (low_prob_rewards / num_rounds) * 100
    
    print("\nReward Statistics:")
    print(f"High probability rewards: {high_prob_rewards}/{num_rounds} ({high_prob_percentage:.2f}%)")
    print(f"Low probability rewards: {low_prob_rewards}/{num_rounds} ({low_prob_percentage:.2f}%)")

    # Save the complete reward sequence to a CSV file
    with open('reward_sequence.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_data)

    print("Reward sequence saved to 'reward_sequence.csv'")

    return sequence

# Generate all sequences needed for the experiment when this module is first imported
TRIAL_SEQUENCE, REVERSAL_ROUNDS = generate_trial_sequence()
REWARD_SEQUENCE = generate_reward_sequence(60, REVERSAL_ROUNDS)