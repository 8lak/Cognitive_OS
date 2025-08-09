# api_client.py

import threading
import time
import google.generativeai as genai
import workspace_manager  # We need to interact with the workspace to update history
import os

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

def get_onetime_response(bot_name, prompt):
    """
    Performs a stateless, one-off query against a bot's history without
    permanently altering its stateful chat session.
    """
    bot_name_proper = workspace_manager.find_bot_by_name_case_insensitive(bot_name)
    if not model or not bot_name_proper or bot_name_proper not in workspace_manager.chat_sessions:
        return f"Simulated onetime response for '{bot_name}' (OFFLINE or Bot session not found)"

    # Get the existing history to provide context for the one-off query
    existing_history = workspace_manager.chat_sessions[bot_name_proper].history
    
    # Prepend the history to the new one-off prompt for context awareness
    # Note: We are not starting a new 'start_chat' session. We are using a direct
    # 'generate_content' call which is stateless by nature.
    
    # We need to format the history correctly for the generate_content call
    contextual_prompt = list(existing_history) # Make a copy
    contextual_prompt.append({'role': 'user', 'parts': [prompt]})

    print(f"\n[...Performing JIT query on '{bot_name_proper}'...]")
    # No spinner for now to keep it simple, can be added later if desired.
    try:
        # Use generate_content for a stateless call
        response = model.generate_content(contextual_prompt)
        return response.text
    except Exception as e:
        return f"--- JIT API Error for {bot_name_proper}: {e} ---"

def launch_prompter_bot_session():
    """
    Launches a temporary, interactive session with the Prompter Bot to help
    the user craft a high-quality prompt. Returns the final generated prompt.
    """
    try:
        template_path = os.path.join("templates", "Prompter_Bot.txt")
        with open(template_path, 'r', encoding='utf-8') as f:
            prompter_system_instruction = f.read()
    except FileNotFoundError:
        print("Critical Error: 'Prompter_Bot.txt' not found in templates directory.")
        return None

    print("\n--- Launching Prompter Bot Session ---")
    print("Engage in a conversation to build your prompt. Type '/done' when you are finished.")
    
    # Create a temporary, one-off chat session for the prompter
    prompter_history = [{'role': 'user', 'parts': [prompter_system_instruction]}]
    # The API expects a 'model' response to the initial user prompt, so we add a boilerplate one.
    prompter_history.append({'role': 'model', 'parts': ["Acknowledged. I am Prompter Bot. What is your high-level goal for the new prompt or bot you wish to create?"]})
    
    prompter_session = model.start_chat(history=prompter_history)
    
    # Print the initial greeting
    print(f"\n[Prompter Bot]: {prompter_history[-1]['parts'][0]}")

    while True:
        user_input = input("[You]: ")
        if user_input.lower() == '/done':
            # When done, ask the bot to synthesize the final prompt
            finalization_prompt = "Excellent. Based on our entire conversation, please now generate the single, final, and complete system prompt for me to use. Do not add any extra commentary, just the prompt itself."
            final_prompt = prompter_session.send_message(finalization_prompt).text
            print("--- Prompter Bot Session Finished ---")
            return final_prompt

        response = prompter_session.send_message(user_input).text
        print(f"[Prompter Bot]: {response}")


