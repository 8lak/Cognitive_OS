import json
import os
import textwrap
import google.generativeai as genai
import threading
import time

# --- Global State ---
workspace = {}          # Holds all bot histories {bot_name: history_list}
chat_sessions = {}      # Holds active API chat sessions {bot_name: session_object}
last_viewed_bot = None  # Remembers the last bot for commands like 'expand'

# --- AI Configuration ---
# PASTE YOUR API KEY HERE
# It's better to use environment variables for security, but this is fine for a personal prototype.
API_KEY = "AIzaSyCiC3emlCs-egKWPNpyFGP7LL8iPHCtAEw" 

model = None
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("--- Google AI Model Initialized Successfully ---")
except Exception as e:
    print(f"--- AI Initialization Error: {e} ---\n--- Running in OFFLINE SIMULATION mode. ---")

# --- Helper Functions ---
def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def find_bot_by_name_case_insensitive(bot_name_query):
    """Finds a bot in the workspace, ignoring case, and returns its proper name."""
    for bot_name in workspace:
        if bot_name.lower() == bot_name_query.lower():
            return bot_name
    return None

# --- Data Loading and Core Logic ---
def load_bot_from_json(filepath):
    """Loads a JSON file as a new bot, preserving its name with spaces."""
    bot_name = os.path.basename(filepath).replace('.json', '')
    history = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # We load the history into the format the Google API needs
        for chunk in data.get("chunkedPrompt", {}).get("chunks", []):
            if chunk.get("isThought"): continue
            content = chunk.get("text", "")
            if not content: continue
            role = "model" if chunk.get("role") == "model" else "user"
            history.append({"role": role, "parts": [content]})
        
        workspace[bot_name] = history
        if model:
            # Start a stateful chat session with the loaded history
            chat_sessions[bot_name] = model.start_chat(history=history)
        print(f"--- Bot '{bot_name}' loaded into workspace. ---")
        return bot_name
    except Exception as e:
        print(f"--- Error loading {filepath}: {e} ---")
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

def get_ai_response(bot_name, prompt):
    """Sends a prompt to a stateful chat session with a live spinner animation."""
    bot_name_proper = find_bot_by_name_case_insensitive(bot_name)
    if not model or bot_name_proper not in chat_sessions:
        return f"Simulated response for '{bot_name}' (OFFLINE)"

    # A shared list to hold the response from the API thread
    response_container = []
    
    # This is the function the API worker thread will run
    def call_api():
        try:
            response = chat_sessions[bot_name_proper].send_message(prompt)
            # IMPORTANT: Add interaction to our history
            workspace[bot_name_proper].append({"role": "user", "parts": [prompt]})
            workspace[bot_name_proper].append({"role": "model", "parts": [response.text]})
            response_container.append(response.text)
        except Exception as e:
            response_container.append(f"--- API Error for {bot_name_proper}: {e} ---")

    # This is the function the animator thread will run
    def animate():
        """The UI function that displays the spinner and timer."""
        # Record the starting time
        start_time = time.time()
        
        while api_thread.is_alive():
            for c in "⢿⣻⣽⣾⣷⣯⣟⡿":
                if not api_thread.is_alive():
                    break
                
                # Calculate elapsed time on each frame
                elapsed = time.time() - start_time
                
                # Update the printout to include the timer
                print(f'\r[...Sending to {bot_name_proper}... {c} ({elapsed:.0f}s)]', end='', flush=True)
                time.sleep(0.1)
    
    # Create and start the threads
    api_thread = threading.Thread(target=call_api)
    animator_thread = threading.Thread(target=animate)
    
    api_thread.start()
    animator_thread.start()
    
    # Wait for the API call to finish
    api_thread.join()
    # The animator will finish on its own on the next cycle
    
    # Clean up the line after the animation is done
    print('\r' + ' ' * 60 + '\r', end='')

    return response_container[0] if response_container else "--- Error: No response received from API thread. ---"

# --- UI and Command Handlers ---
def display_workspace_status():
    """Shows all bots currently loaded in the workspace."""
    clear_screen()
    print("--- Workspace Status ---")
    if not workspace:
        print("Workspace is empty. Use 'load' to add a bot.")
    else:
        print("Bots loaded:")
        for bot_name, history in workspace.items():
            print(f"- {bot_name} ({len(history)} messages)")
    print("------------------------\n")

def display_bot_preview(bot_name):
    """Prints a two-column preview of a specific bot's conversation."""
    global last_viewed_bot
    clear_screen()
    
    bot_name_proper = find_bot_by_name_case_insensitive(bot_name)
    if not bot_name_proper:
        print(f"Error: Bot '{bot_name}' not found.")
        return

    print(f"--- Conversation Preview: {bot_name_proper} ---\n")
    last_viewed_bot = bot_name_proper # Remember this for the 'expand' command

    display_list = []
    user_msg_counter, assistant_msg_counter = 1, 1
    for msg in workspace[bot_name_proper]:
        role, content = msg.get("role"), msg.get("parts", [""])[0]
        display_msg = {"content": content}
        if role == "user":
            display_msg.update({"id": f"U{user_msg_counter}", "role": "user"})
            user_msg_counter += 1
        elif role == "model":
            display_msg.update({"id": f"A{assistant_msg_counter}", "role": "assistant"})
            assistant_msg_counter += 1
        else: continue
        display_list.append(display_msg)
    
    user_messages = [msg for msg in display_list if msg['role'] == 'user']
    assistant_messages = [msg for msg in display_list if msg['role'] == 'assistant']
    
    col_width = 45
    header = f"{{:<{col_width}}}   {{:<{col_width}}}"
    row = f"{{:<{col_width}}} | {{:<{col_width}}}"
    
    print(header.format("--- USER ---", "--- ASSISTANT ---"))
    print(header.format("="*col_width, "="*col_width))

    for i in range(max(len(user_messages), len(assistant_messages))):
        user_col = ""
        if i < len(user_messages):
            msg = user_messages[i]
            preview = textwrap.shorten(msg['content'].replace('\n', ' '), width=col_width-8, placeholder="...")
            user_col = f"[{msg['id']}] {preview}"
        assistant_col = ""
        if i < len(assistant_messages):
            msg = assistant_messages[i]
            preview = textwrap.shorten(msg['content'].replace('\n', ' '), width=col_width-8, placeholder="...")
            assistant_col = f"[{msg['id']}] {preview}"
        print(row.format(user_col, assistant_col))
    print("\n" + "="*(col_width*2 + 3))

def handle_expand_message(display_id):
    """Finds and prints the full content of a single message from the last viewed bot."""
    if not last_viewed_bot:
        print("--- Error: Use 'show <bot_name>' first to select a conversation. ---")
        return

    message = find_message_by_display_id(last_viewed_bot, display_id)
    if message:
        clear_screen()
        role = "User" if message.get("role") == "user" else "Assistant"
        print(f"--- Full Text for Message {display_id.upper()} from '{last_viewed_bot}' ({role}) ---")
        content = message.get("parts", [""])[0]
        print(textwrap.fill(content, width=90))
        print("-" * 60)
    else:
        print(f"--- Error: Message ID {display_id} not found in '{last_viewed_bot}'. ---")

def handle_interactive_forward():
    """A guided wizard for the forward command."""
    clear_screen()
    print("--- Interactive Forward ---")
    
    while True:
        origin_query = input("1. Enter name of ORIGIN bot (to forward FROM): ")
        origin_bot = find_bot_by_name_case_insensitive(origin_query)
        if origin_bot:
            display_bot_preview(origin_bot); break
        print(f"  Error: Bot '{origin_query}' not found. Try again.")

    msg_id = input(f"\n2. Enter Message ID from '{origin_bot}' to forward (e.g., A5): ")
    source_message = find_message_by_display_id(origin_bot, msg_id)
    if not source_message:
        print(f"  Error: Message '{msg_id}' not found. Aborting."); return

    while True:
        target_query = input("3. Enter name of TARGET bot (to forward TO): ")
        target_bot = find_bot_by_name_case_insensitive(target_query)
        if target_bot: break
        print(f"  Error: Bot '{target_query}' not found. Try again.")

    new_prompt = input(f"4. Enter your new prompt for '{target_bot}': ")
    source_content = source_message.get("parts", [""])[0]
    final_prompt = (
        f"I am providing you with context from a different agent, '{origin_bot}'.\n"
        f"--- CONTEXT from {origin_bot} (msg {msg_id}) ---\n"
        f"{source_content}\n"
        f"--- END CONTEXT ---\n\n"
        f"Based on that context, here is my request: {new_prompt}"
    )

    response_text = get_ai_response(target_bot, final_prompt)
    print(f"\n--- Response from {target_bot} ---")
    print(response_text)
    print("-" * 60)

def main_loop():
    """The main command handler loop."""
    display_workspace_status()
    while True:
        print("\nCommands: [status], [load], [show <bot>], [expand <id>], [forward], [chat <bot>], [exit]")
        cmd_line = input("> ").strip().split()
        cmd = cmd_line[0].lower() if cmd_line else ""

        if cmd == "status": display_workspace_status()
        elif cmd == "exit": break
        elif not cmd: continue
        
        elif cmd == "load":
            filepath = input("Enter path to JSON file to load as a bot: ")
            load_bot_from_json(filepath)
            display_workspace_status()

        elif cmd == "show" and len(cmd_line) > 1:
            bot_query = ' '.join(cmd_line[1:])
            display_bot_preview(bot_query)

        elif cmd == "expand" and len(cmd_line) > 1:
            handle_expand_message(cmd_line[1])
        
        elif cmd == "forward":
            handle_interactive_forward()

        elif cmd == "chat" and len(cmd_line) > 1:
            bot_query = ' '.join(cmd_line[1:])
            bot_name = find_bot_by_name_case_insensitive(bot_query)
            if bot_name:
                prompt = input(f"Chatting with '{bot_name}': ")
                response = get_ai_response(bot_name, prompt)
                print(f"\n--- Response from {bot_name} ---\n{response}")
            else:
                print(f"Error: Bot '{bot_query}' not found.")
        
        else:
            print("Unknown command or missing arguments.")

if __name__ == "__main__":
    main_loop()