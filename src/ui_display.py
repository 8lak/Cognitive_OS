# ui_display.py

import os
import textwrap
import workspace_manager # This module needs to get data from the workspace

# --- Helper ---
def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

# --- Main Display Functions ---
def display_workspace_status():
    """Prints the status of all bots currently loaded in the workspace."""
    clear_screen()
    print("--- Workspace Status ---")
    status_data = workspace_manager.get_workspace_status()
    if not status_data:
        print("Workspace is empty. Use 'project' to populate workspace.")
    else:
        print("Bots loaded:")
        for bot_name, msg_count in status_data.items():
            print(f"- {bot_name} ({msg_count} messages)")
    print("------------------------\n")

def display_bot_preview(bot_name):
    """Prints a two-column preview of a specific bot's conversation."""
    clear_screen()
    
    bot_name_proper = workspace_manager.find_bot_by_name_case_insensitive(bot_name)
    if not bot_name_proper:
        print(f"Error: Bot '{bot_name}' not found.")
        return None

    print(f"--- Conversation Preview: {bot_name_proper} ---\n")
    
    history = workspace_manager.get_bot_history(bot_name_proper)
    if not history:
        print("History is empty.")
        return bot_name_proper # Return the name even if history is empty

    # Generate the display list with temporary IDs on the fly
    display_list = []
    user_msg_counter, assistant_msg_counter = 1, 1
    for msg in history:
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
    
    return bot_name_proper # Return the proper name so 'main' knows what was viewed

def display_full_message(bot_name, display_id):
    """Finds and prints the full content of a single message from the specified bot."""
    message = workspace_manager.find_message_by_display_id(bot_name, display_id)
    if message:
        clear_screen()
        role = "User" if message.get("role") == "user" else "Assistant"
        print(f"--- Full Text for Message {display_id.upper()} from '{bot_name}' ({role}) ---")
        content = message.get("parts", [""])[0]
        print(textwrap.fill(content, width=90))
        print("-" * 60)
    else:
        print(f"--- Error: Message ID {display_id} not found in '{bot_name}'. ---")