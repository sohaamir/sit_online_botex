# main_task/bot_behaviour.py

import random

def bot_play_round(player):
    # Make random choices and bets for the bot
    player.choice1 = random.choice(['left', 'right'])
    player.bet1 = random.randint(1, 3)
    player.choice2 = random.choice(['left', 'right'])
    player.bet2 = random.randint(1, 3)
    
    # Set chosen images based on choices
    player.chosen_image_one = player.left_image if player.choice1 == 'left' else player.right_image
    player.chosen_image_two = player.left_image if player.choice2 == 'left' else player.right_image
    
    # Set binary representations of choices
    player.chosen_image_one_binary = 1 if player.chosen_image_one == 'option1A.bmp' else 2
    player.chosen_image_two_binary = 1 if player.chosen_image_two == 'option1A.bmp' else 2
    
    # Set computer choice flags
    player.computer_choice_one = True
    player.computer_choice_two = True
    
    # Set choice accuracies
    player.choice1_accuracy = player.chosen_image_one == player.group.seventy_percent_image
    player.choice2_accuracy = player.chosen_image_two == player.group.seventy_percent_image
    
    # Calculate switch vs stay
    player.switch_vs_stay = 1 if player.chosen_image_one != player.chosen_image_two else 0