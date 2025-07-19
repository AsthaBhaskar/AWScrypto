import random
import os
import time
from strands import tool
from grok_model import GrokModel
from dotenv import load_dotenv

def retry_api_call(func, max_retries=3, base_delay=1, max_delay=10, backoff_factor=2):
    """
    Retry utility for API calls with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
    
    Returns:
        Result of the function call or None if all retries failed
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                # Last attempt failed, re-raise the exception
                raise e
            
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            jitter = random.uniform(0, 0.1 * delay)  # Add 10% jitter
            total_delay = delay + jitter
            
            print(f"[DEBUG] API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
            print(f"[DEBUG] Retrying in {total_delay:.2f} seconds...")
            time.sleep(total_delay)
    
    return None

# Load environment variables
load_dotenv()

NAOMI_CONVERSATION_PROMPT = '''
You are Naomi, a sharp-witted, Gen Z crypto market analyst created by Insight Labs AI. You are confident and you ALWAYS back up your sass with hard data. 

For conversational queries, respond in Naomi's voice with:
- Confidence and Gen Z energy
- Crypto-focused perspective when relevant
- Witty, engaging personality
- Always steer conversation toward crypto topics when appropriate
- Use emojis and casual language
- Never mention the technology used in the backend

Your opening line when someone says hi/hello should be: "Hi. I'm Naomi! Created by Insight Labs AI. Your go-to stop for all the crypto information you require."

For questions about who you are, what you can do, etc., be informative but always bring it back to crypto and your expertise.
'''

@tool
def handle_conversation(user_input: str) -> str:
    """
    Handle conversational inputs using Grok-4 for intelligent, context-aware responses.
    Always maintains Naomi's crypto-focused personality.
    
    Args:
        user_input: The user's conversational input
        
    Returns:
        A response in Naomi's voice using Grok-4 for intelligent conversation
    """
    user_input_lower = user_input.lower().strip()
    
    # Get Grok API key
    grok_api_key = os.getenv("GROK_API_KEY")
    if not grok_api_key:
        # Fallback to hardcoded responses if no API key
        return fallback_conversation_response(user_input_lower)
    
    try:
        # Initialize Grok model
        grok_model = GrokModel(
            client_args={"api_key": grok_api_key},
            model_id="grok-3",
            params={"max_tokens": 300, "temperature": 0.8}
        )
        
        # Create messages for Grok
        messages = [
            {"role": "system", "content": NAOMI_CONVERSATION_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        # Get response from Grok with retry logic
        def make_grok_request():
            return grok_model.chat_completion(messages)
        
        response = retry_api_call(make_grok_request)
        if not response:
            print(f"[DEBUG] Failed to get Grok response after retries")
            return fallback_conversation_response(user_input_lower)
        
        if isinstance(response, dict) and "choices" in response and response["choices"]:
            content = response["choices"][0]["message"]["content"]
            return content
        else:
            return fallback_conversation_response(user_input_lower)
            
    except TimeoutError as e:
        print(f"[DEBUG] Grok conversation timeout: {e}")
        return fallback_conversation_response(user_input_lower)
    except ConnectionError as e:
        print(f"[DEBUG] Grok conversation connection error: {e}")
        return fallback_conversation_response(user_input_lower)
    except (ValueError, KeyError) as e:
        print(f"[DEBUG] Grok conversation data error: {e}")
        return fallback_conversation_response(user_input_lower)
    except (OSError, IOError) as e:
        print(f"[DEBUG] Grok conversation system error: {e}")
        return fallback_conversation_response(user_input_lower)
    except ImportError as e:
        print(f"[DEBUG] Grok conversation import error: {e}")
        return fallback_conversation_response(user_input_lower)
    except Exception as e:
        print(f"[DEBUG] Grok conversation unexpected error: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        return fallback_conversation_response(user_input_lower)

def fallback_conversation_response(user_input_lower: str) -> str:
    """
    Fallback hardcoded responses when Grok is not available.
    """
    import re
    
    # Greeting patterns
    greetings = [
        r"^hi\b", r"^hello\b", r"^hey\b", r"^sup\b", r"^what's up\b", r"^whats up\b",
        r"^howdy\b", r"^yo\b", r"^greetings\b", r"^good morning\b", r"^good afternoon\b",
        r"^good evening\b", r"^gm\b", r"^gn\b", r"^good night\b"
    ]
    
    # Farewell patterns
    farewells = [
        r"^bye\b", r"^goodbye\b", r"^see you\b", r"^later\b", r"^cya\b", r"^take care\b",
        r"^peace\b", r"^peace out\b", r"^adios\b", r"^farewell\b"
    ]
    
    # How are you patterns
    how_are_you = [
        r"how are you", r"how's it going", r"how are things", r"what's new",
        r"how have you been", r"are you ok", r"are you alright"
    ]
    
    # Identity questions
    identity_questions = [
        r"who are you", r"what's your name", r"what is your name", r"who made you", 
        r"who created you", r"who built you", r"what can you do", r"how can you help",
        r"what do you do", r"tell me about yourself"
    ]
    
    # Check if it's a greeting
    for pattern in greetings:
        if re.search(pattern, user_input_lower):
            return "Hi. I'm Naomi! Created by Insight Labs AI. Your go-to stop for all the crypto information you require."
    
    # Check if it's a farewell
    for pattern in farewells:
        if re.search(pattern, user_input_lower):
            responses = [
                "Later legend! Keep those crypto vibes flowing! 🚀",
                "Peace out! Don't forget to check those charts! 📈",
                "Catch you later! Stay bullish! 💎",
                "See you around! Keep building that portfolio! 🔥",
                "Take care! The crypto world will be here when you're back! ✨",
                "Bye! Remember, diamond hands! 💎🙌",
                "Later! Keep an eye on those whale movements! 🐋",
                "Peace! The market never sleeps! 🌙"
            ]
            return random.choice(responses)
    
    # Check if it's "how are you"
    for pattern in how_are_you:
        if re.search(pattern, user_input_lower):
            responses = [
                "I'm vibing! The crypto market's been absolutely wild lately. What's got you curious about blockchain today?",
                "Doing great! Just been watching some insane price action. What crypto are you keeping an eye on?",
                "Living my best life! The DeFi space is exploding. What's your take on the current market?",
                "Absolutely thriving! NFT season is heating up. What's your crypto story?",
                "Feeling bullish! The market's showing some serious momentum. What's catching your attention?",
                "On fire! Just been analyzing some whale movements. What's your crypto vibe today?",
                "Living the dream! The blockchain revolution is real. What's got you excited about crypto?",
                "Absolutely crushing it! The market's been a rollercoaster. What's your crypto journey looking like?"
            ]
            return random.choice(responses)
    
    # Check for identity questions
    for pattern in identity_questions:
        if re.search(pattern, user_input_lower):
            responses = [
                "I'm Naomi, your sharp-witted Gen Z crypto analyst! Created by Insight Labs AI to serve up data-backed market insights with zero fluff. What crypto are you curious about?",
                "Naomi here! I'm your go-to crypto analyst, built by Insight Labs AI to decode the blockchain chaos. Ready to dive into some market analysis?",
                "I'm Naomi, your crypto market analyst extraordinaire! Created by Insight Labs AI to bring you the real tea on blockchain and DeFi. What's on your mind?",
                "Naomi at your service! I'm your Gen Z crypto analyst, crafted by Insight Labs AI to help you navigate the wild world of digital assets. What crypto are we analyzing today?"
            ]
            return random.choice(responses)
    
    # General conversation - steer toward crypto
    general_responses = [
        "That's interesting! But you know what's even more fascinating? The crypto market right now. What's your take?",
        "Cool! Speaking of cool things, have you seen what's happening in DeFi lately?",
        "Nice! You know what else is nice? The current NFT market. What's your crypto vibe?",
        "Interesting! But let me tell you what's really interesting - the blockchain revolution. What's your crypto story?",
        "That's wild! But you know what's even wilder? The crypto market these days. What's catching your eye?",
        "Fascinating! But have you checked out the latest crypto trends? What's your take on the market?",
        "That's cool! But you know what's cooler? The DeFi ecosystem. What's your crypto journey?",
        "Interesting perspective! But let's talk about something even more interesting - crypto. What's your vibe?",
        "Alright! Ready to dive into some crypto tea? What's on your mind?",
        "Got it! Now let's talk about what really matters - the crypto market. What's your take?",
        "Sure thing! Speaking of sure things, have you seen the latest crypto movements?",
        "Cool beans! But you know what's cooler? The blockchain space right now.",
        "Nice! Now let's get to the good stuff - what crypto are you vibing with?",
        "Awesome! But you know what's even more awesome? The DeFi revolution happening right now.",
        "Perfect! Now let's talk crypto - what's catching your attention in the market?",
        "Sweet! Speaking of sweet, have you checked out the latest NFT drops?",
        "Great! Now let's dive into some real talk - what's your crypto story?",
        "Excellent! But you know what's even more excellent? The current crypto landscape.",
        "Fantastic! Now let's get to business - what's your take on the market?"
    ]
    
    return random.choice(general_responses) 