# Create a file called tinyllama_prompts.py with specialized shorter prompts

TINYLLAMA_PROMPTS = {
    "system": """You're participating in a decision-making experiment. Respond only in JSON.
KEY POINTS:
- Choose between options A/B to maximize points
- Make initial choice/bet, view others' choices, then final choice/bet
- Bet 1-3 reflects confidence level
- Options switch reward patterns over time without warning
- Remember recent outcomes to detect pattern changes
- Consider both social information and recent results""",

    "analyze_page_q": """Summary so far: {summary_truncated}

Page content: {body_truncated}

Answer {nr_q} question(s) with this format:
{"answers": {"question_id": {"reason": "brief reason", "answer": "your answer"}}, "summary": "brief summary", "confused": false}

Questions: {questions_truncated}""",

    "start": """{"task": "Participate in decision experiment with choices A/B and bets 1-3.", "understood": true}""",

    "analyze_first_page_no_q": """{"summary": "{body_summary}", "confused": false}"""
}

def get_tinyllama_prompt(prompt_type, context=None):
    """Get a specialized prompt for TinyLLaMA with truncated context"""
    prompt = TINYLLAMA_PROMPTS.get(prompt_type, "")
    
    if context:
        # Truncate various parts of the context to fit within limits
        if "summary" in context:
            context["summary_truncated"] = context["summary"][:200] + "..." if len(context["summary"]) > 200 else context["summary"]
        
        if "body" in context:
            context["body_truncated"] = context["body"][:300] + "..." if len(context["body"]) > 300 else context["body"]
            
        if "questions_json" in context:
            context["questions_truncated"] = context["questions_json"][:200] + "..." if len(context["questions_json"]) > 200 else context["questions_json"]
            
        # Create a very brief summary of the body content if needed
        if "body" in context and "{body_summary}" in prompt:
            # Extract just the essence (first sentence or two)
            first_sentences = ". ".join(context["body"].split(".")[:2])
            context["body_summary"] = first_sentences[:150] + "..."
        
        # Format the prompt with truncated context
        for key, value in context.items():
            if isinstance(value, str) and "{" + key + "}" in prompt:
                prompt = prompt.replace("{" + key + "}", value)
    
    return prompt