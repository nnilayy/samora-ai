# Function descriptions for LLM tool calling
# These descriptions help the LLM understand when to call each function

# Description for the put_on_hold function
HOLD_FUNCTION_DESCRIPTION = """Put the conversation on hold when the user indicates they need a moment. 
Call this when user says things like:
- "hold on", "hold please", "one moment"
- "give me a minute", "give me a second"  
- "I need to think", "let me think"
- "wait", "pause", "just a moment"
- "I'm talking to someone else"
- "be right back", "brb"
- "hang on"
- "stay on the line"
The bot will wait silently until the user says a wake phrase like 'hey samora' or 'I'm back'."""

# Description for the end_call function
END_CALL_FUNCTION_DESCRIPTION = """End the call gracefully when the user indicates they are done.
Call this when user says things like:
- "That's all", "I'm done", "Nothing else"
- "No thanks", "I'm good", "No more questions"
- "Goodbye", "Bye", "Take care", "See you"
- "I have nothing else", "That's everything"
- Responds negatively to 'Is there anything else I can help with?'
- "No", "Nope" (when asked if they need more help)
The bot will say a friendly goodbye and then end the call."""
