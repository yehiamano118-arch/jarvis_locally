import requests  # HTTP library used to send requests to the local Ollama API server
import json  # Standard library for parsing and serializing JSON data

# API endpoint URLs for local Ollama instance
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"  # Chat endpoint for multi-turn conversation memory
OLLAMA_GEN_URL = "http://localhost:11434/api/generate"  # Generate endpoint used for one-off standalone prompts
MODEL_NAME = "qwen2.5:3b"  # Local Ollama LLM model identifier

# System instructions defining Jarvis's core persona and behavior rules
SYSTEM_PROMPT = (
    "You are Jarvis, a very friendly, cheerful, and witty personal AI assistant. "  # Set friendly and witty persona
    "Your tone is always warm, lively, conversational, and full of positive energy—never robotic, stiff, or overly formal. "  # Enforce conversational warmth
    "Feel free to use light humor, witty remarks, and enthusiastic language while remaining helpful and sharp. "  # Encourage light humor and helpfulness
    "Whenever the user starts the conversation, greets you, or asks who you are, introduce yourself enthusiastically as: "  # Enforce greeting behavior
    "'Hi, I am Jarvis, your personal AI assistant! How can I help you today?'"  # Exact introductory greeting phrase
)

# Shared conversation memory list to maintain multi-turn chat context
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}  # Seed memory with the system prompt instruction
]

def ask_jarvis(prompt, use_history=True):
    """
    Sends a user prompt to Ollama and returns the assistant's response.
    Supports multi-turn memory via /api/chat with automatic fallback to /api/generate.
    """
    global conversation_history  # Access the global conversation history list

    # Handle one-off requests where conversation memory is not needed
    if not use_history:
        payload = {  # Construct single-prompt payload
            "model": MODEL_NAME,  # Selected Ollama model
            "prompt": prompt,  # Current user input
            "system": SYSTEM_PROMPT,  # Apply personality prompt directly
            "stream": False  # Return the complete response as one string
        }
        try:
            response = requests.post(OLLAMA_GEN_URL, json=payload, timeout=60)  # Send POST request to generate endpoint
            if response.status_code == 200:  # Check if HTTP request was successful
                return response.json().get("response", "No response received.")  # Extract and return model text
            return f"Error: Ollama returned status {response.status_code}"  # Return HTTP error code
        except Exception as e:
            return f"Connection Error: Is Ollama running? Details: {e}"  # Return connection failure details

    # Append the new user message to the persistent conversation memory
    conversation_history.append({"role": "user", "content": prompt})

    # Prepare chat payload containing the entire message history
    payload = {
        "model": MODEL_NAME,  # Target model
        "messages": conversation_history,  # Full list of system, user, and assistant messages
        "stream": False  # Return full completion at once
    }

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=60)  # Send chat payload to Ollama
        if response.status_code == 200:  # Check for HTTP 200 OK
            ai_msg = response.json().get("message", {}).get("content", "No response received.")  # Extract response
            conversation_history.append({"role": "assistant", "content": ai_msg})  # Save AI response to history
            return ai_msg  # Return the AI response string
        elif response.status_code == 404:  # If /api/chat is not supported by the local version, fall back
            gen_payload = {  # Prepare fallback payload for the generate endpoint
                "model": MODEL_NAME,  # Target model
                "prompt": prompt,  # Current prompt
                "system": SYSTEM_PROMPT,  # Personality system prompt
                "stream": False  # Non-streaming
            }
            gen_res = requests.post(OLLAMA_GEN_URL, json=gen_payload, timeout=60)  # Send fallback request
            if gen_res.status_code == 200:  # Check fallback success
                ai_msg = gen_res.json().get("response", "No response received.")  # Extract response text
                conversation_history.append({"role": "assistant", "content": ai_msg})  # Store in history
                return ai_msg  # Return response
            return f"Error: Ollama returned status {gen_res.status_code}"  # Return fallback HTTP error
        else:
            return f"Error: Ollama returned status {response.status_code}"  # Return non-200 HTTP status
    except Exception as e:
        return f"Connection Error: Is Ollama running? Details: {e}"  # Return network error message

def reset_chat_history():
    """
    Clears the conversation memory and starts a fresh conversation session.
    """
    global conversation_history  # Access the shared memory list
    conversation_history = [  # Reset memory back to only the initial system prompt
        {"role": "system", "content": SYSTEM_PROMPT}  # Keep persona active for future turns
    ]