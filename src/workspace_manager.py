# workspace_manager.py

import os
import json

# --- Module-level State ---
# This module "owns" the data. No other module should modify these directly.
workspace = {}          # Holds all bot histories {bot_name: history_list}
chat_sessions = {}      # Holds active API chat sessions {bot_name: session_object}

# --- Core Data Functions ---

def load_bot_from_json(filepath, model_instance):
    """
    Loads a JSON file as a new bot, creates its chat session, and adds it to the workspace.
    This function now requires the 'model_instance' to be passed in from the api_client.
    """
    bot_name = os.path.basename(filepath).replace('.json', '')
    history = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for chunk in data.get("chunkedPrompt", {}).get("chunks", []):
            if chunk.get("isThought"): continue
            content = chunk.get("text", "")
            if not content: continue
            role = "model" if chunk.get("role") == "model" else "user"
            history.append({"role": role, "parts": [content]})
        
        workspace[bot_name] = history
        
        # If we have a live AI model, create a stateful chat session for the new bot.
        if model_instance:
            chat_sessions[bot_name] = model_instance.start_chat(history=history)
            
        print(f"--- Bot '{bot_name}' loaded into workspace. ---")
        return bot_name
    except Exception as e:
        print(f"--- Error loading {filepath}: {e} ---")
        return None

def find_bot_by_name_case_insensitive(bot_name_query):
    """Finds a bot in the workspace, ignoring case, and returns its proper name."""
    for bot_name in workspace:
        if bot_name.lower() == bot_name_query.lower():
            return bot_name
    return None

def find_message_by_display_id(bot_name, display_id):
    """Finds a message in a bot's history using its temporary display ID (e.g., 'A5')."""
    bot_name_proper = find_bot_by_name_case_insensitive(bot_name)
    if not bot_name_proper: return None

    user_msg_counter = 1
    assistant_msg_counter = 1
    for message_data in workspace[bot_name_proper]:
        current_display_id = ""
        role = message_data.get("role")
        if role == "user":
            current_display_id = f"U{user_msg_counter}"
            user_msg_counter += 1
        elif role == "model":
            current_display_id = f"A{assistant_msg_counter}"
            assistant_msg_counter += 1
        
        if current_display_id.lower() == display_id.lower():
            return message_data
    return None

def get_workspace_status():
    """Returns a dictionary representing the current state of the workspace."""
    return {name: len(history) for name, history in workspace.items()}

def get_bot_history(bot_name):
    """Safely retrieves the history for a given bot."""
    bot_name_proper = find_bot_by_name_case_insensitive(bot_name)
    return workspace.get(bot_name_proper)

def add_message_to_history(bot_name, role, prompt_or_response):
    """Adds a new user prompt or model response to a bot's history."""
    bot_name_proper = find_bot_by_name_case_insensitive(bot_name)
    if bot_name_proper and bot_name_proper in workspace:
        workspace[bot_name_proper].append({"role": role, "parts": [prompt_or_response]})

def clear_workspace():
    """Clears all bots and sessions from the current workspace."""
    # Ensure we are modifying the global variables in this module
    global workspace, chat_sessions
    workspace = {}          # Re-initialize to empty dictionaries
    chat_sessions = {}

def create_new_bot(project_name, bot_name_raw, system_instruction, model_instance):
    """
    Creates a new bot .json file, saves it, and loads it into the workspace.
    """
    # Sanitize the name for the filename
    bot_name = bot_name_raw.replace(' ', '_')
    filename = f"{bot_name}.json"
    filepath = os.path.join("projects", project_name, filename)

    if os.path.exists(filepath):
        print(f"Error: Bot '{bot_name}' already exists in project '{project_name}'.")
        return None

    # Create a JSON structure that our load_bot_from_json function can understand.
    # The system instruction is treated as the very first "user" message in the history.
    initial_data = {
      "chunkedPrompt": {
        "chunks": [
          {
            "text": system_instruction,
            "role": "user"
          }
        ]
      }
    }

    try:
        # Write the new file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2)
        
        print(f"Bot '{bot_name_raw}' file created successfully.")
        
        # Immediately load the new bot into the active workspace for instant use
        return load_bot_from_json(filepath, model_instance)

    except Exception as e:
        print(f"An error occurred while creating the bot file: {e}")
        return None
    
def save_bot_state(project_name, bot_name):
    """
    Saves the full, current conversation history from a bot's active session
    back to its .json file on disk.
    """
    if bot_name not in chat_sessions:
        # This can happen if a bot file exists but failed to load into a session
        # print(f"Debug: Bot '{bot_name}' has no active session to save.")
        return False

    # Find the correct file path. We need to handle names with spaces vs. underscores.
    # The key in the workspace is the user-facing name, which might have spaces.
    bot_filename_base = bot_name.replace(' ', '_')
    
    # We must find the exact filename, which may or may not have .json
    project_path = os.path.join("projects", project_name)
    target_filepath = None
    for item in os.listdir(project_path):
        item_path = os.path.join(project_path, item)
        item_name_no_ext = item.replace('.json', '') if item.endswith('.json') else item
        if os.path.isfile(item_path) and item_name_no_ext == bot_filename_base:
            target_filepath = item_path
            break
    
    if not target_filepath:
        # print(f"Debug: Could not find matching file for bot '{bot_name}' to save.")
        return False

    # Get the complete history from the live chat session object.
    # The Google AI library conveniently stores this for us.
    live_history = chat_sessions[bot_name].history
    
    # Reformat the history back into the simple dictionary structure our loader expects.
    # This ensures a symmetrical save/load process.
    history_as_dicts = []
    for message in live_history:
        # The 'parts' object is an iterable, we get the text from the first part.
        content = "".join(part.text for part in message.parts)
        history_as_dicts.append({"role": message.role, "parts": [content]})
        
    # Re-create the top-level JSON structure.
    # NOTE: We are overwriting the "chunkedPrompt" for simplicity. V2.1 might separate initial prompt from history.
    save_data = {
        "chunkedPrompt": {
            "chunks": [{"text": msg["parts"][0], "role": msg["role"]} for msg in history_as_dicts]
        }
    }

    try:
        # Overwrite the original file with the new, complete history.
        with open(target_filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)
        return True
    except Exception as e:
        print(f"An error occurred while saving '{bot_name}': {e}")
        return False

def create_standalone_bot(bot_name_raw, system_instruction, model_instance):
    """Creates a new standalone bot .json file directly in the projects folder."""
    # This is almost identical to create_new_bot, but saves to the root 'projects' path
    bot_name = bot_name_raw.replace(' ', '_')
    # We need a unique name to avoid conflicts, let's just save it with the extension
    filename = f"{bot_name}.json" 
    filepath = os.path.join("projects", filename)

    if os.path.exists(filepath):
        print(f"Error: A bot or project named '{bot_name}' already exists."); return None
        
    initial_data = {
      "chunkedPrompt": { "chunks": [{"text": system_instruction, "role": "user"}]}
    }
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2)
        print(f"Standalone bot '{bot_name_raw}' created successfully.")
        return load_bot_from_json(filepath, model_instance)
    except Exception as e:
        print(f"An error occurred: {e}"); return None



