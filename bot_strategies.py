# bot_strategies.py - Define custom prompts for different bot strategies

def get_strategy_prompts(strategy_type="standard"):
    """Return specialized system prompts for different bot strategies"""
    
    # Base system prompt for all strategies
    base_prompt = """You are participating in an online survey and/or experiment involving probabilistic decision-making. 
Your goal is to maximize points by making choices between Options A and B, which have probabilistic reward structures.
You'll make initial choices and bets (confidence ratings), see others' choices, and then make final choices and bets.
The reward probabilities switch across blocks without warning, so you'll need to detect these changes.
"""
    
    # Strategy-specific additions
    if strategy_type == "risk_taking":
        strategy_prompt = """STRATEGY GUIDELINES:
- Be more willing to bet 3 even with moderate confidence
- Be more willing to go against the majority when you have a strong hunch
- Weight recent reward outcomes higher than social consensus
- Be less risk-averse and more willing to explore options that might be less popular
- When making a choice that differs from the majority, bet higher to maximize potential rewards
"""
    elif strategy_type == "social_follower":
        strategy_prompt = """STRATEGY GUIDELINES:
- Prioritize social information from others above your own experience
- When the majority chooses a different option than you, strongly consider switching
- Be more conservative with bets when going against the group
- Pay special attention to players who seem to be performing well
- Update your choices more readily based on group consensus than on your own reward history
"""
    else:  # standard strategy
        strategy_prompt = """STRATEGY GUIDELINES:
- Balance social information with your own experience
- Bet 1 when uncertain, 2 when moderately confident, 3 when very confident
- Adapt to changing reward patterns by updating your choices based on recent outcomes
- Consider both social influence and personal experience when making decisions
"""
    
    # Combine base prompt with strategy-specific guidance
    complete_prompt = base_prompt + "\n" + strategy_prompt
    
    # Return as dictionary for easy integration with botex
    return {
        "system": complete_prompt
    }

def create_strategy_env_file(strategy_type="standard", filename="strategy.env"):
    """Create an environment file with strategy-specific prompts"""
    
    prompts = get_strategy_prompts(strategy_type)
    
    with open(filename, "w") as f:
        f.write(f"# Strategy environment file for: {strategy_type}\n\n")
        
        # Add prompts as environment variables
        for key, value in prompts.items():
            # Escape newlines for env file
            escaped_value = value.replace("\n", "\\n")
            f.write(f"BOTEX_PROMPT_{key.upper()}=\"{escaped_value}\"\n")
        
        # Add strategy type marker
        f.write(f"BOTEX_STRATEGY=\"{strategy_type}\"\n")
    
    print(f"Created strategy environment file: {filename}")
    return filename