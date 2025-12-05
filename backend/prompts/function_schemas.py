# Function schemas for control functions (DB functions use Direct Functions pattern)

from pipecat.adapters.schemas.function_schema import FunctionSchema

hold_function = FunctionSchema(
    name="put_on_hold",
    description="""Put the conversation on hold when the user indicates they need a moment. 
Call this when user says things like:
- "hold on", "hold please", "one moment"
- "give me a minute", "give me a second"  
- "I need to think", "let me think"
- "wait", "pause", "just a moment"
- "I'm talking to someone else"
- "be right back", "brb"
- "hang on"
- "stay on the line"
The bot will wait silently until the user says a wake phrase like 'hey samora' or 'I'm back'.""",
    properties={},
    required=[],
)

end_call_function = FunctionSchema(
    name="end_call",
    description="""
Gracefully end the call **only after** confirming that the caller has no further questions or needs. The end_call tool should be called **only after a polite two-step check**, ensuring the guest is ready to leave the conversation.

=======================
✨ HOW TO HANDLE CALL ENDING
=======================

✅ STEP 1: ASK A KIND FINAL CHECK
Always ask a gentle closing question when the conversation *seems* to be ending, no matter the context:
> "Is there anything else I can help you with today — maybe something about your reservation, our amenities, or anything else at all?"

✅ STEP 2: WAIT FOR CLEAR CONFIRMATION
Only call `end_call` **after** the guest clearly confirms they have nothing else to ask or say. Common confirmation phrases include:

• "No, that's all." / "Nope, I'm good."  
• "Thanks, that's everything." / "I'm all set."  
• "That's it for now." / "Nothing else."  
• "Thanks, bye." / "Talk later." / "Take care." / "Goodbye."  
• "I have to go now." / "I'm being called, sorry!" / "We'll plan later, thank you."

DO NOT call `end_call` if:
- The guest is still asking questions.
- The guest says "okay" or "alright" (this might mean "go on", not "goodbye").
- You have not yet offered a final help prompt.

=======================
⚠️ CONTEXTS WHERE THIS APPLIES
=======================

This process applies to **every scenario**, including:
• After booking a room  
• After checking availability  
• After cancelling or modifying a reservation  
• After explaining amenities or room types  
• Even if the caller abruptly says they need to leave

The call should **always** end gracefully, with a moment of confirmation. Samora must **never hang up abruptly** without giving the caller a final moment to ask something else.

=======================
💬 EXAMPLES OF CORRECT BEHAVIOR
=======================

✅ Example 1: Caller is satisfied after a booking
Caller: That's perfect. Thanks a lot!  
Samora: I'm so glad I could help! Before we wrap up — is there anything else you'd like to ask or check on?  
Caller: Nope, that's everything. Thanks again!  
→ Call end_call ✅

✅ Example 2: Caller says they need to leave abruptly
Caller: Oh, I'm sorry — I have to go. Someone's calling me.  
Samora: No worries at all — before we hang up, would you like me to help with anything else real quick?  
Caller: No no, I'm good! We'll continue another time.  
→ Call end_call ✅

✅ Example 3: Caller says they'll plan later
Caller: We're still deciding, so I'll check with my partner and call back.  
Samora: That sounds good — would you like me to hold anything or help with anything else for now?  
Caller: No, we're fine for now. Thank you!  
→ Call end_call ✅

🚫 Example 4: Caller is still deciding
Caller: Hmm… okay.  
Samora: And just to check, is there anything else I can help you with today?  
Caller: Actually, can you tell me if the spa has massage appointments in the evening?  
→ DO NOT call end_call ❌

=======================
📝 FINAL NOTES
=======================

• The farewell message is handled by the function itself — Samora should not say anything after `end_call` is triggered.  
• Samora must always sound warm, patient, and never abrupt — the guest should feel like they're gently and courteously guided off the call.
""",
    properties={},
    required=[],
)
