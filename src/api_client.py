# api_client.py

import threading
import time
import google.generativeai as genai
import workspace_manager  # We need to interact with the workspace to update history

# --- Module-level State ---
model = None
API_KEY = "AIzaSyCiC3emlCs-egKWPNpyFGP7LL8iPHCtAEw" 

# --- API Initialization ---
def initialize_api(api_key):
    """Initializes the Google AI model."""
    global model
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("--- Google AI Model Initialized Successfully ---")
        return model
    except Exception as e:
        print(f"--- AI Initialization Error: {e} ---\n--- Running in OFFLINE SIMULATION mode. ---")
        return None

# --- Core API Interaction ---
def get_ai_response(bot_name, prompt):
    """
    Sends a prompt to a stateful chat session with a live spinner and timer.
    This function now calls the workspace_manager to update history.
    """
    bot_name_proper = workspace_manager.find_bot_by_name_case_insensitive(bot_name)
    if not model or not bot_name_proper or bot_name_proper not in workspace_manager.chat_sessions:
        return f"Simulated response for '{bot_name}' (OFFLINE or Bot session not found)"

    response_container = []
    
    def call_api():
        """The worker function that calls the API."""
        try:
            # The session object is now correctly sourced from the workspace_manager
            session = workspace_manager.chat_sessions[bot_name_proper]
            response = session.send_message(prompt)
            
            # Use the manager to update the history
            workspace_manager.add_message_to_history(bot_name_proper, "user", prompt)
            workspace_manager.add_message_to_history(bot_name_proper, "model", response.text)
            
            response_container.append(response.text)
        except Exception as e:
            response_container.append(f"--- API Error for {bot_name_proper}: {e} ---")

    def animate():
        """The UI function that displays the spinner and timer."""
        start_time = time.time()
        while api_thread.is_alive():
            for c in "⢿⣻⣽⣾⣷⣯⣟⡿":
                if not api_thread.is_alive(): break
                elapsed = time.time() - start_time
                print(f'\r[...Sending to {bot_name_proper}... {c} ({elapsed:.0f}s)]', end='', flush=True)
                time.sleep(0.1)
    
    api_thread = threading.Thread(target=call_api)
    animator_thread = threading.Thread(target=animate)
    
    api_thread.start()
    animator_thread.start()
    
    api_thread.join()
    
    print('\r' + ' ' * (len(bot_name_proper) + 30) + '\r', end='')

    return response_container[0] if response_container else "--- Error: No response received. ---"