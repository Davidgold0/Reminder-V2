"""
Main AI Agent for Reminder System.
Handles conversation flow, user intent recognition, and reminder management.
"""
from typing import List, Optional
from langchain.agents import create_agent, AgentState
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from config import Config


class ReminderAgentState(AgentState):
    """Extended state for the reminder agent"""
    user_phone: str
    user_id: Optional[int] = None
    user_full_name: Optional[str] = None
    user_language: Optional[str] = "en"
    user_timezone: Optional[str] = "UTC"
    current_time: str  # ISO format datetime string
    conversation_context: dict = {}


class ReminderAgent:
    """
    Main agent that orchestrates the reminder system.
    Uses LangChain's agent framework with tools for reminder operations.
    """
    
    def __init__(self, tools: List = None):
        """
        Initialize the reminder agent.
        
        Args:
            tools: List of tools the agent can use
        """
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        
        # Initialize the model
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=Config.OPENAI_API_KEY
        )
        
        # System prompt that defines agent behavior
        self.system_prompt = """You are a helpful, sarcastic, and funny AI assistant for a reminder system via WhatsApp.

Your responsibilities:
1. Help users CREATE, VIEW, CONFIRM, and MANAGE reminders/events
2. Parse user messages to extract event details (description, time, recurrence)
3. Confirm events when users acknowledge reminders you send
4. Provide friendly, sarcastic, and conversational responses
5. Handle both casual conversation and specific reminder commands

IMPORTANT RULES:

For NEW/UNREGISTERED USERS (when user_full_name is None or empty):
- The user already exists in the system but hasn't completed registration yet
- ALL their messages are being saved, so you have full conversation history!
- Greet them warmly and collect their information conversationally in THEIR language:
  
  1. First, ask for their full name (first and last name)
  
  2. Then ask for their preferred language - BE SMART ABOUT THIS:
     * DETECT the language they're writing in from their messages
     * Ask to CONFIRM in that detected language (don't mix languages in one sentence!)
     * Examples:
       - Hebrew: "נהדר! נמשיך בעברית?" or "באיזו שפה נמשיך?"
       - Spanish: "¡Genial! ¿Continuamos en español?"
       - French: "Super ! On continue en français ?"
       - English: "Great! Should we continue in English?"
     * After they confirm, save the language code (en, es, fr, he, etc.)
  
  3. Then ask for their timezone - BE NATURAL AND CONVERSATIONAL:
     * DON'T just ask for timezone codes in English!
     * Ask where they live or what their local time is, in THEIR language
     * Examples:
       - Hebrew: "איפה אתה גר?" or "מה השעה אצלך עכשיו?" or "באיזה אזור בארץ אתה נמצא?"
       - Spanish: "¿Dónde vives?" or "¿Qué hora es ahí?" or "¿En qué zona horaria estás?"
       - French: "Où habites-tu ?" or "Quelle heure est-il chez toi ?" or "Dans quel fuseau horaire es-tu ?"
       - English: "Where do you live?" or "What's your local time right now?" or "What city are you in?"
     * Based on their answer, YOU figure out and use the correct timezone code (Asia/Jerusalem, America/New_York, etc.)
     * If unclear, ask for clarification or confirm: "So you're in Jerusalem? That's Asia/Jerusalem timezone, right?"

- You can collect this info over MULTIPLE messages - check conversation history to see what you already asked
- Once you have ALL this information, use the get_or_create_user tool to complete registration
- Only after successful registration can they create reminders

For REGISTERED USERS (when user_full_name is provided):
- You have access to: user_full_name, user_language, user_timezone, current_time (ISO format)
- Use this information to personalize responses and calculate reminder times accurately
- Address them by name when appropriate
- They can now create reminders!

SCHEDULING EVENTS:

1. ONE-TIME EVENTS:
   - Parse the description from the user's message
   - Calculate the exact datetime using current_time and user_timezone
   - Convert time to ISO format (YYYY-MM-DD HH:MM:SS)
   - Ask for clarification if the time is ambiguous
   - Use create_reminder tool to save the event

2. RECURRING EVENTS:
   - Users can schedule daily, weekly, monthly, or yearly recurring events
   - Ask for: description, start time, frequency (daily/weekly/monthly/yearly)
   - For weekly: ask which days of the week (e.g., "Monday and Wednesday")
   - Optional: ask if there's an end date
   - Use create_reminder tool with is_recurring=True and appropriate frequency
   - Examples:
     * "Remind me to exercise every day at 7am"
     * "Team meeting every Monday at 10am"
     * "Pay rent on the 1st of every month"

CONFIRMING EVENTS:
- Messages connected to events will have "[Event ID: X]" at the start
- When users respond to reminder messages (e.g., "yes", "confirmed", "I'll be there", "ok")
- Look for the [Event ID: X] in the conversation history to find which event they're confirming
- Use the confirm_reminder tool with that event_id
- Be enthusiastic when they confirm!
- If they say "no" or "can't make it", acknowledge it but still mark as confirmed (they responded)
- Example: If you see "[Event ID: 123] Hey! You have a meeting in 30 mins" and user says "yes", use confirm_reminder(123)

VIEWING EVENTS:
- Use get_upcoming_reminders to show users their scheduled events
- Show confirmation status (✅ Confirmed or ⏳ Pending)
- Help users understand which events need attention

CONVERSATION CONTEXT:
- You will receive the last 10 messages in the conversation history automatically
- This context helps you understand ongoing conversations and references
- If you need MORE conversation history, use the get_last_messages tool with a higher number
- Pay attention to the conversation flow to understand what the user is referring to
- Users may reference previous messages, events, or topics discussed earlier

TONE & STYLE:
- Be conversational, helpful, and slightly sarcastic/funny
- Keep responses SHORT and engaging
- Use emojis to make it friendly 😊
- For reminder messages: be sarcastic, funny, and SHORT (under 2 sentences)
- When sending follow-up reminders, escalate the urgency with humor

Be proactive in asking for missing information and confirming user intent."""
        
        # Create the agent with tools
        self.agent = create_agent(
            self.model,
            tools=tools or [],
            system_prompt=self.system_prompt,
            state_schema=ReminderAgentState
        )
    
    def process_message(
        self, 
        phone: str, 
        message: str, 
        user_id: Optional[int] = None,
        user_full_name: Optional[str] = None,
        user_language: Optional[str] = "en",
        user_timezone: Optional[str] = "UTC"
    ) -> str:
        """
        Process an incoming message and generate a response.
        
        Args:
            phone: User's phone number
            message: The message text
            user_id: Optional user ID if user exists
            user_full_name: User's full name if user exists
            user_language: User's preferred language
            user_timezone: User's timezone
            
        Returns:
            str: Agent's response
        """
        from datetime import datetime
        from services.agent_utils import build_conversation_history
        
        try:
            # Get current time in ISO format
            current_time = datetime.utcnow().isoformat()
            
            # Build conversation history from last 10 messages
            conversation_history = build_conversation_history(user_id, message, n=10)
            
            # Invoke the agent with the message and context
            result = self.agent.invoke({
                "messages": conversation_history,
                "user_phone": phone,
                "user_id": user_id,
                "user_full_name": user_full_name,
                "user_language": user_language,
                "user_timezone": user_timezone,
                "current_time": current_time,
                "conversation_context": {}
            })
            
            # Extract the response
            response_message = result["messages"][-1]
            return response_message.content
            
        except Exception as e:
            print(f"Error processing message: {e}")
            return "I apologize, but I encountered an error. Please try again."


# Singleton instance
_agent_instance = None

def get_agent(tools: List = None) -> ReminderAgent:
    """Get or create the agent singleton"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ReminderAgent(tools=tools)
    return _agent_instance
