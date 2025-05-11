#!/usr/bin/env python3
"""
estimate_tokens.py - Estimate token usage and cost for botex experiments

This tool analyzes the social influence task structure and estimates token usage and cost
for running experiments with different LLM models. It provides estimates for OpenAI, 
Anthropic, and Google Gemini models.

Usage:
    python estimate_tokens.py [--rounds N] [--participants N] [--max-tokens N] [--strategy STRATEGY]

Examples:
    # Estimate for default configuration (64 rounds, 1 participant)
    python estimate_tokens.py
    
    # Estimate for 10 participants with 32 rounds
    python estimate_tokens.py --rounds 32 --participants 10
    
    # Estimate with specific token limit and strategy
    python estimate_tokens.py --max-tokens 2048 --strategy social_follower
"""

from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path
import tiktoken
import argparse
import json
import glob
import os
import re

# Default pricing per 1M tokens (in USD)
# Averages are taken for some output token prices where it differs for token length (mainly Google models)

PRICING = {
    "openai": {
        "gpt-4.1-nano": {"input": 0.15, "output": 0.60},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    },
    "anthropic": {
        "claude-3.7-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3.5-haiku": {"input": 0.80, "output": 4.00},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    },
    "gemini": {
        "gemini-2.5-flash-preview": {"input": 0.15, "output": 0.60},
        "gemini-2.5-pro-preview": {"input": 1.25, "output": 12.50},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
        "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 7.50},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.45},
    }
}

def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Estimate token usage and cost for botex experiments")
    parser.add_argument("--rounds", type=int, default=64, 
                        help="Number of rounds in the experiment (default: 64)")
    parser.add_argument("--participants", type=int, default=1, 
                        help="Number of participants (default: 1)")
    parser.add_argument("--max-tokens", type=int, default=1024,
                        help="Maximum tokens per response (default: 1024)")
    parser.add_argument("--strategy", choices=["standard", "risk_taking", "social_follower"],
                        default="standard", help="Bot strategy (default: standard)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed breakdown of token usage")
    return parser.parse_args()

def count_tokens(text, model="gpt-4"):
    """Count the number of tokens in a string using tiktoken"""
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception as e:
        # Fallback to approximate token count (about 4 chars per token)
        return len(text) // 4

def get_prompts(strategy="standard"):
    """Get the prompts used in the experiment with the specified strategy"""
    # This function reproduces the prompts from the botex experiment
    base_system_prompt = """You are participating in an online survey and/or experiment, potentially involving other human or artificial participants. The user provides you with a series of independent prompts. 
        Most prompts will also contain scraped text data from a webpage containing the survey/experiment, and detailed tasks for you on how to analyze this text data. 
        The scraped web page texts contain instructions on how the experiment/survey is conducted. These instructions might include information on how participants are being compensated or paid for their participation. 
        If this is the case, please act as if this compensation also applies to you and make sure to include this information in the summary so that you will recall it in later prompts. 
        Most importantly, the scraped texts can include questions and/or tasks which the user wants you to answer. They might also contain comprehension checks, repeated information from prior pages, and potentially text bits that do not directly belong to the experiment. 

        EXPERIMENT OVERVIEW:
        - You are participating in a social experiment where your goal is to maximize points by making choices and placing bets. 
        - This is a probabilistic reversal learning task with two options (A and B). The reward contingencies switch across blocks without warning. 
        - Within each block, one option is more likely to give rewards, but rewards are probabilistic - even the better option will sometimes give losses.
        - You'll make choices and bets (reflecting choice confidence), in a group of 5 participants, who are learning the task at the same time as you. 
        - Therefore, you will be able to see others' choices; the extent to which this influences your own choices is up to you.

        HISTORICAL INFORMATION USAGE:
        - Because the task is probabilistic, you should try to learn from your own rewards and the choices of others over time
        - You should be influenced by the choices of others in the immediate past respective to your choice
        - You should also be influenced by your own immediate choices and feedback
        - However, you should retain only a vague memory of the last few rounds for your own feedback
        - Remember that a round consists of an initial choice, initial bet, second choice and second bet
        
        When interacting with the experiment, analyze each page carefully and respond with a valid JSON."""
    
    # Strategy-specific prompts
    if strategy == "risk_taking":
        # More risk-taking strategy
        strategy_prompt = """
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A
        - Throughout the task, be FLEXIBLE and somewhat BOLD in your choices
        - You should be willing to go against the majority opinion more often
        - When you see a potential pattern, act on it more aggressively
        - Feel completely free to update your choice both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets should reflect a higher risk tolerance than average
        - Be more willing to place bet 3 (high confidence) even with moderate certainty
        - Bet 1 only when genuinely uncertain, prefer bet 2 or 3 when you have any confidence
        - You should prioritize higher rewards by placing higher bets more often
        - Never bet 1 more than two rounds in a row - show more confidence!
        - Betting conservatively is often suboptimal - to maximize your score, TAKE RISKS
        """
    elif strategy == "social_follower":
        # More socially influenced strategy
        strategy_prompt = """
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A
        - Throughout the task, prioritize SOCIAL INFORMATION over your own experiences
        - When the majority of other players choose an option, strongly consider following them
        - Be more likely to switch your choice if you see others choosing differently
        - Still be flexible in your choices, but weight social information more heavily
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets should directly reflect your confidence in your choice
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - When following the majority, bet higher (more confidently)
        - When going against the majority, bet lower (less confidently)
        - Adjust your bet based on how unanimous the other players are
        - Betting conservatively when uncertain is your preferred approach
        """
    else:  # standard strategy
        strategy_prompt = """
        CHOICE STRATEGY:
        - In the very first round only, you should choose randomly between B and A
        - Throughout the task, be FLEXIBLE in your choices based on both social information and your own experience
        - Remember that the other players are learning the task at the same time as you
        - Feel completely free to update your choice both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence
        
        BETTING STRATEGY:
        - Your bets should directly reflect your confidence in your choice
        - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
        - Feel completely free to change your bet both WITHIN trials and ACROSS trials
        - Never fixate on one strategy - constantly adapt based on changing evidence
        - Betting conservatively is often a suboptimal strategy - vary your bets based on genuine confidence
        """
    
    # Combine base prompt with strategy-specific instructions
    combined_system_prompt = base_system_prompt + "\n\n" + strategy_prompt
    
    analyze_page_q = """Perfect. This is your summary of the survey/experiment so far: \n\n {summary} \n\n You have now proceeded to the next page. This is the body text of the web page: \n\n {body} \n\n 

    I need you to answer {nr_q} question(s) and update your summary. When making choices and bets, follow these critical guidelines:

    CHOICES:
    - Throughout the task, be FLEXIBLE in your choices based on both social information and your own experience
    - You should be influenced by the choices of others in the immediate past respective to your choice
    - You should also be influenced by your own immediate choices and feedback
    - However, you should also retain a vague memory of the last few rounds regarding your own feedback
    - Feel completely free to update your choice appropriately both WITHIN trials and ACROSS trials
    - Never fixate on one strategy - constantly adapt based on changing evidence

    BETTING:
    - Bet 1 when uncertain about your choice, bet 2 when moderately confident, and bet 3 when fairly confident
    - Betting conservatively can be a suboptimal strategy. To score the most points, vary your bets based on genuine confidence
    - Feel completely free to change your bet appropriately both WITHIN trials and ACROSS trials

    HISTORICAL INFORMATION USAGE:
    When explaining your reasoning for CHOICES, you MUST specifically reference:
    1. WHICH round or rounds influenced your current decision
    2. WHAT pattern of rewards you've observed and remember
    3. HOW you're weighing social information against your own experience

    Your reasoning should demonstrate the integration of historical data, not just the most recent round.
    
    The following JSON string contains the questions: {questions_json} 

    For each identified question, you must provide two variables: 'reason' contains your reasoning or thought that leads you to a response or answer and 'answer' which contains your response.

    Taken together, a correct answer to a text with two questions would have the form {{""answers"": {{""ID of first question"": {{""reason"": ""Your reasoning for how you want to answer the first question"", ""answer"":""Your final answer to the first question""}}, ""ID of the second question"": {{""reason"": ""Your reasoning for how you want to answer the second question"", ""answer"": ""Your final answer to the second question""}}}},""summary"": ""Your summary"", ""confused"": ""set to `true` if you are confused by any part of the instructions, otherwise set it to `false`""}}"""
    
    end_prompt = """Perfect. This concludes the survey/experiment and our conversation. This is your summary of the completed survey/experiment: \n\n {summary} \n\n Do you have any final remarks about the survey/experiment and how you answered it, or about its implementation in this conversation that you want to share? Then please provide your answer as JSON, using the variable 'remarks'. If you have no final remarks, respond with {{remarks: 'none'}}. If you are confused, please indicate this by setting the 'confused' key to true."""
    
    return {
        "system": combined_system_prompt,
        "analyze_page_q": analyze_page_q,
        "end": end_prompt
    }

def get_page_contents():
    """Extract typical content for each page in the experiment based on HTML files"""
    # Read HTML files to extract typical page content
    pages = {}
    
    # Read welcome page content
    welcome_content = """
    PARTICIPANT INFORMATION
    Please read the following information carefully.
    
    In this experiment, you will make a series of choices between two options, one of which will reward you by giving you points, whilst the other will reduce your score.
    
    You will be playing with four other players in real time, who will concurrently make the same choices.
    
    However, there is no competition or co-operation with other players, your aim is solely to maximise the amount of points that you score which will be converted into a bonus payment at the end of the experiment. The more points you score, the higher your bonus payment will be!
    
    You will receive financial compensation of 10 US Dollars (USD) per hour, which coincides with completing both parts. You may also receive a bonus payment of up to 3 US Dollars (USD) based on your performance in the task.
    
    Once you have read through this information and are happy to proceed, please press the 'Next' button below. You will receive detailed instructions on how to complete the task.
    """
    pages["Welcome"] = welcome_content.strip()
    
    # Read task structure page content
    task_structure_content = """
    Reward Structure
    
    Task Overview
    
    In this experiment, you will make a series of choices between two options, 'Option A' and 'Option B' over several rounds. In each round one Option will reward you by giving you points, whilst the other Option will give you a loss, reducing your score.
    
    However the reward contingency is probabilistic, meaning that one option is more likely to give you a reward than a loss, and the other is more likely to give you a loss than a reward.
    
    The task is also a reversal learning task, meaning that the reward contingencies will switch at unspecified points. This will happen multiple times across the task, such that the 'better' option will become the 'worse' option and vice versa.
    
    You will be playing with four other players in real time, who will also make the same choices.
    
    During the task, you will be able to make an initial choice and bet (confidence rating) in that choice, before seeing the initial choices of others within the group.
    
    After this, you are provided the opportunity to revise your choice and bet in response to the choices made by others.
    
    You may choose to either trust your own learning experience through trial and error and/or take decisions from others in the group into consideration, as some of the other players might learn faster than others.
    
    However, there is no competition or cooperation with other players. Your aim is solely to maximize the amount of points that you score, which will be converted into a bonus payment at the end of the experiment. The more points you score, the higher your bonus payment will be!
    
    As a result, the experiment aims understand how social learning from others and individual learning from one's own experience contribute to social decision-making.
    
    Reward Structure
    
    In each round, one option will reward you whilst the other will lower your score. Which option does which is the same for all players in the group. For example, Option A will either be correct for all players in the group, or incorrect for all players in the group. It will not be correct or incorrect for some and not others.
    
    Reflecting the 'reversal learning' nature of the task, the rounds are split into several blocks. Within each block, both options will give you wins and losses, such that one option is more likely to give you points (but will sometimes give a loss) whilst the other is more likely to give you a loss (but will sometimes reward you). In other words, the reward structure is probabilistic, meaning that within each block, one option will will give you a reward most of the time, and the other will give you a loss most of the time.
    
    The reward structure is not random, it is probabilistically determined for one option to be more/less advantageous than the other within each block.
    
    However, this will switch multiple times across the task, such that the 'better' option will become the 'worse' option and vice versa.
    
    For example, whilst it may be better overall to choose one option over the other in one block, in the next block it will be the other way round.
    
    This is a very important aspect of the game, because if the option gave you the same outcome every time in each block, you would always know which one to pick and when exactly the reversals happen!
    
    However, in the very first block, whether 'Option A' or 'Option B' is the more rewarding option will be selected at random. It will subsequently alternate from then onwards.
    
    For example, if 'Option A' was randomly selected to be the more rewarding option in the first block, 'Option B' will be more rewarding in the second block, 'Option A' in the third and so on. The same pattern applies if 'Option B' is randomly selected to be the more rewarding option in the first block; 'Option A' will be more rewarding in the second block, Option B in the third and so on. Ultimately, it will never be the case that 'Option A' or 'Option B' is the more rewarding option in two blocks in a row.
    
    The challenge of the game is that when and how often the switches take place are unknown to you. You will not know when the switch has occurred and a new block has started. You should therefore pay attention to the feedback and adjust your choices accordingly.
    
    As mentioned, over the course of the game, you may choose to either trust your own learning experience through trial and error and/or take decisions from others in the group into consideration, as some of the other players might learn faster than others.
    
    It is completely up to you to extent in which you are influenced by the decisions of others, or to trust your own experience.
    
    However, remember that there is no competition or co-operation with other players, your aim is solely to maximise the amount of points that you score.
    
    When you are ready, please press the button below to move onto the next page of instructions which will describe the task structure in more detail.
    """
    pages["TaskStructure"] = task_structure_content.strip()
    
    # Read FirstDecisions page content
    first_decisions_content = """
    Initial Choice and Bet
    
    Instructions
    
    You have started a new round. Please make your initial choice and bet for this round, then submit the form.
    
    Make your initial choice
    
    Select your choice:
    A
    B
    
    Make your initial bet
    
    Select your bet:
    1
    2
    3
    """
    pages["FirstDecisions"] = first_decisions_content.strip()
    
    # Read SecondDecisions page content
    second_decisions_content = """
    Other Players' Initial Choices and making your Second Choice and Bet
    
    Instructions
    
    You are in the same round, and will now see what the other players chose for their initial choice.
    
    After reviewing their choices, you can make your second choice and bet.
    
    Other Players' Initial Choices
    
    Here are the initial choices that the other players in your group made:
    Player 1: A
    Player 2: B
    Player 3: A
    Player 4: B
    
    Your Initial Choice and Bet
    
    Your initial choice was: A
    Your initial bet was: 2
    
    Your Second Choice
    
    Select your second choice:
    A
    B
    
    Your Second Bet
    
    Select your second bet:
    1
    2
    3
    """
    pages["SecondDecisions"] = second_decisions_content.strip()
    
    # Read RoundResults page content
    round_results_content = """
    Round Results
    
    Instructions
    
    Please review the results for this round. When you are ready, click the 'Next' button to continue to the next round.
    
    Your Result
    
    Your second choice was A.
    This choice was correct.
    
    You gained 40 points in this round.
    
    Other Players' Results
    
    Here are the results for the other players in your group:
    
    Player	Second Choice	Outcome
    Player 1	Option A	Correct
    Player 2	Option B	Incorrect
    Player 3	Option A	Correct
    Player 4	Option B	Incorrect
    """
    pages["RoundResults"] = round_results_content.strip()
    
    # Read Comprehension page content (for first round)
    comprehension_content = """
    Comprehension Checks
    
    This is a comprehension check to test your understanding of the task. Please answer all questions and submit the form by pressing the 'Next' button. You will receive feedback on your answers in the next page.
    
    Question 1
    
    You make a first bet of 2, but change to 3 for your second bet. You do not change your chosen option. During the round feedback you learn that the option chosen was not rewarded on this trial.
    
    How many points do you earn/lose for your second choice?
    
    40 points
    minus 40 points
    60 points
    minus 60 points
    
    Question 2
    
    Please select Option 3.
    
    Option 1
    Option 2
    Option 3
    Option 4
    
    Question 3
    
    Which of the following accurately describes how your bonus payment is calculated?
    
    From your initial choice and bet only
    From your second bet and choice only
    From either the first and second choices/bets but randomly on each trial
    From both the first and second choices/bets on each trial
    
    Question 4
    
    Which accurately describes how likely each of the options will give a reward/loss in each block?
    
    Randomly determined
    One option will give you a reward everytime, and the other will give you a loss everytime
    One option will give you a reward randomly, and the other will give you a loss randomly
    One option will give you a reward most of the time, and the other will give you a loss most of the time
    """
    pages["Comprehension"] = comprehension_content.strip()
    
    return pages

def estimate_tokens_per_round(page_contents, prompts, summary_growth_factor=1.2, max_tokens=1024):
    """Estimate tokens used per round of the experiment"""
    # Initialize token estimates
    token_estimates = {
        "input": {},
        "output": {}
    }
    
    # Generate a sample summary for each round
    summary_length = 500  # Initial summary length
    
    # First round includes welcome, task structure, round structure, comprehension
    # Calculate tokens for first round
    first_round_pages = ["Welcome", "TaskStructure", "RoundStructure", "Comprehension", 
                      "ComprehensionResults", "Transition", "FirstDecisions", 
                      "SecondDecisions", "RoundResults"]
    
    token_estimates["input"]["round1"] = 0
    token_estimates["output"]["round1"] = 0
    
    # System prompt tokens (counted once)
    system_tokens = count_tokens(prompts["system"])
    token_estimates["input"]["system"] = system_tokens
    
    # Process each page in first round
    for page in first_round_pages:
        page_content = page_contents.get(page, f"Sample content for {page}")
        
        # Format the prompt template
        if page in ["FirstDecisions", "SecondDecisions", "RoundResults"]:
            # For these pages, use the analyze_page_q prompt
            prompt = prompts["analyze_page_q"].format(
                summary="Initial summary.",
                body=page_content,
                nr_q=2,  # Estimate 2 questions per page
                questions_json='{"id_choice1": {"question_type": "radio", "question_label": "Select your choice"}, "id_bet1": {"question_type": "radio", "question_label": "Select your bet"}}'
            )
            
            # Count tokens in this prompt
            prompt_tokens = count_tokens(prompt)
            token_estimates["input"]["round1"] += prompt_tokens
            
            # Estimate tokens in response
            # For FirstDecisions and SecondDecisions, estimate more tokens for reasoning
            output_tokens = min(1000, max_tokens)  # Conservative estimate
            token_estimates["output"]["round1"] += output_tokens
            
            # Summary grows with each page
            summary_length = summary_length * summary_growth_factor
        else:
            # For other pages, estimate a simpler prompt
            prompt_tokens = count_tokens(page_content) + 200  # Base prompt + content
            token_estimates["input"]["round1"] += prompt_tokens
            
            # Simpler responses for instruction pages
            output_tokens = min(500, max_tokens)
            token_estimates["output"]["round1"] += output_tokens
    
    # Standard rounds (2 through end) consist of FirstDecisions, SecondDecisions, RoundResults
    token_estimates["input"]["standard_round"] = 0
    token_estimates["output"]["standard_round"] = 0
    
    # Process standard round pages
    standard_round_pages = ["FirstDecisions", "SecondDecisions", "RoundResults"]
    
    for page in standard_round_pages:
        page_content = page_contents.get(page, f"Sample content for {page}")
        
        # Format prompt with growing summary
        prompt = prompts["analyze_page_q"].format(
            summary=f"Summary of length ~{summary_length} characters.",
            body=page_content,
            nr_q=2,  # Estimate 2 questions per page
            questions_json='{"id_choice1": {"question_type": "radio", "question_label": "Select your choice"}, "id_bet1": {"question_type": "radio", "question_label": "Select your bet"}}'
        )
        
        # Count tokens
        prompt_tokens = count_tokens(prompt)
        token_estimates["input"]["standard_round"] += prompt_tokens
        
        # Estimate response tokens
        output_tokens = min(800, max_tokens)  # Conservative estimate
        token_estimates["output"]["standard_round"] += output_tokens
        
        # Summary grows with each page
        summary_length = summary_length * summary_growth_factor
    
    # Final round includes the end prompt
    end_prompt = prompts["end"].format(
        summary=f"Final summary of length ~{summary_length} characters."
    )
    token_estimates["input"]["final"] = count_tokens(end_prompt)
    token_estimates["output"]["final"] = min(800, max_tokens)
    
    return token_estimates

def calculate_total_tokens(token_estimates, rounds=64):
    """Calculate total tokens for the entire experiment"""
    total_tokens = {
        "input": 0,
        "output": 0
    }
    
    # Add system prompt tokens (only counted once)
    total_tokens["input"] += token_estimates["input"]["system"]
    
    # Add first round tokens
    total_tokens["input"] += token_estimates["input"]["round1"]
    total_tokens["output"] += token_estimates["output"]["round1"]
    
    # Add tokens for rounds 2 through N-1
    standard_rounds = rounds - 2  # Subtract first and last round
    if standard_rounds > 0:
        total_tokens["input"] += standard_rounds * token_estimates["input"]["standard_round"]
        total_tokens["output"] += standard_rounds * token_estimates["output"]["standard_round"]
    
    # Add final round tokens
    total_tokens["input"] += token_estimates["input"]["standard_round"]  # Regular pages of final round
    total_tokens["input"] += token_estimates["input"]["final"]  # Final prompt
    total_tokens["output"] += token_estimates["output"]["standard_round"]
    total_tokens["output"] += token_estimates["output"]["final"]
    
    # Calculate total
    total_tokens["total"] = total_tokens["input"] + total_tokens["output"]
    
    return total_tokens

def calculate_cost(tokens, model="gpt-4.1-nano"):
    """Calculate cost based on token usage and model pricing"""
    costs = {}
    
    # Extract model family and variant
    if "/" in model:
        provider, model_name = model.split("/", 1)
    else:
        # Try to infer provider
        if model.startswith("gpt"):
            provider = "openai"
            model_name = model
        elif model.startswith("claude"):
            provider = "anthropic"
            model_name = model
        elif model.startswith("gemini"):
            provider = "gemini"
            model_name = model
        else:
            provider = "unknown"
            model_name = model
    
    # Get base model name for pricing
    base_model = model_name.split("-")[0] + "-" + model_name.split("-")[1]
    
    # Get pricing for the model or use default
    model_pricing = None
    if provider in PRICING:
        # Find the closest match
        for price_model in PRICING[provider]:
            if base_model in price_model or price_model in base_model:
                model_pricing = PRICING[provider][price_model]
                break
        
        # If no match found, use the first model in the provider
        if model_pricing is None and PRICING[provider]:
            first_model = next(iter(PRICING[provider]))
            model_pricing = PRICING[provider][first_model]
            print(f"Warning: No pricing found for {model_name}. Using {first_model} pricing as estimate.")
    
    # If still no pricing, use a default
    if model_pricing is None:
        model_pricing = {"input": 1.0, "output": 2.0}  # Default pricing
        print(f"Warning: No pricing found for {provider}/{model_name}. Using default pricing.")
    
    # Calculate costs
    costs["input"] = (tokens["input"] / 1_000_000) * model_pricing["input"]
    costs["output"] = (tokens["output"] / 1_000_000) * model_pricing["output"]
    costs["total"] = costs["input"] + costs["output"]
    
    return costs

def format_token_estimates(token_estimates, verbose=False):
    """Format token estimates for display"""
    if verbose:
        result = "Token Usage Breakdown:\n\n"
        result += f"System prompt: {token_estimates['input']['system']:,} tokens\n\n"
        result += f"First round input: {token_estimates['input']['round1']:,} tokens\n"
        result += f"First round output: {token_estimates['output']['round1']:,} tokens\n\n"
        result += f"Standard round input: {token_estimates['input']['standard_round']:,} tokens\n"
        result += f"Standard round output: {token_estimates['output']['standard_round']:,} tokens\n\n"
        result += f"Final round additional input: {token_estimates['input']['final']:,} tokens\n"
        result += f"Final round additional output: {token_estimates['output']['final']:,} tokens\n"
    else:
        result = ""
    
    return result

def main():
    """Main function to estimate token usage and cost"""
    # Load environment variables
    load_dotenv("botex.env")
    
    # Parse arguments
    args = get_args()
    
    # Get prompts based on strategy
    prompts = get_prompts(args.strategy)
    
    # Get page contents
    page_contents = get_page_contents()
    
    # Estimate tokens per round
    token_estimates = estimate_tokens_per_round(
        page_contents, 
        prompts, 
        summary_growth_factor=1.2, 
        max_tokens=args.max_tokens
    )
    
    # Calculate total tokens
    total_tokens = calculate_total_tokens(token_estimates, args.rounds)
    
    # Print results
    print("\n" + "="*80)
    print(f"TOKEN USAGE ESTIMATE FOR SOCIAL INFLUENCE TASK")
    print("="*80)
    print(f"Configuration:")
    print(f"- Rounds: {args.rounds}")
    print(f"- Participants: {args.participants}")
    print(f"- Max tokens per response: {args.max_tokens}")
    print(f"- Strategy: {args.strategy}")
    print("\n" + "-"*80)
    
    # Print token breakdown if verbose
    if args.verbose:
        print(format_token_estimates(token_estimates, verbose=True))
        print("-"*80)
    
    # Print total tokens per participant
    print(f"ESTIMATED TOKENS PER PARTICIPANT:")
    print(f"- Input tokens: {total_tokens['input']:,}")
    print(f"- Output tokens: {total_tokens['output']:,}")
    print(f"- Total tokens: {total_tokens['total']:,}")
    print("\n" + "-"*80)
    
    # Print total tokens for all participants
    all_participants_tokens = {
        "input": total_tokens["input"] * args.participants,
        "output": total_tokens["output"] * args.participants,
        "total": total_tokens["total"] * args.participants
    }
    
    print(f"ESTIMATED TOKENS FOR ALL {args.participants} PARTICIPANTS:")
    print(f"- Input tokens: {all_participants_tokens['input']:,}")
    print(f"- Output tokens: {all_participants_tokens['output']:,}")
    print(f"- Total tokens: {all_participants_tokens['total']:,}")
    print("\n" + "-"*80)
    
    # Calculate and print costs for different models
    print(f"ESTIMATED COSTS FOR {args.participants} PARTICIPANTS:")
    
    # Models to check
    models = [
        # OpenAI models
        "gpt-4.1-nano-2025-04-14",
        "gpt-4",
        "gpt-3.5-turbo",
        # Anthropic models
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
        # Gemini models
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro"
    ]
    
    # Calculate and print costs for each model
    for model in models:
        cost = calculate_cost(all_participants_tokens, model)
        print(f"- {model}: ${cost['total']:.2f} (${cost['input']:.2f} input + ${cost['output']:.2f} output)")
    
    print("\n" + "="*80)
    print("NOTE: These estimates are approximate and based on current pricing.")
    print("      Actual usage and costs may vary based on specific interactions.")
    print("="*80 + "\n")
    
    # Save results to file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results = {
        "config": {
            "rounds": args.rounds,
            "participants": args.participants,
            "max_tokens": args.max_tokens,
            "strategy": args.strategy
        },
        "token_estimates": token_estimates,
        "total_tokens_per_participant": total_tokens,
        "total_tokens_all_participants": all_participants_tokens,
        "costs": {model: calculate_cost(all_participants_tokens, model) for model in models}
    }
    
    with open(f"token_estimate_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Detailed results saved to token_estimate_{timestamp}.json")

if __name__ == "__main__":
    import time
    main()