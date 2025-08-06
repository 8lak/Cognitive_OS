# main.py

import os
import json
import workspace_manager
import api_client
import ui_display

# --- Main Application State ---
# This is the "controller" layer. It holds the app's UI state.
active_project= None
last_viewed_bot = None

# --- Configuration ---
# Your API key is now cleanly stored in the main entry point of the application.
API_KEY = "AIzaSyCiC3emlCs-egKWPNpyFGP7LL8iPHCtAEw" 

# --- Command Handler Functions ---
# These functions act as the bridge between the UI and the backend modules.

def handle_show(cmd_line):
    """Handles the 'show' command."""
    global last_viewed_bot
    if len(cmd_line) < 2:
        print("Usage: show <bot_name>")
        return
    bot_query = ' '.join(cmd_line[1:])
    # The UI function returns the proper name of the bot that was viewed.
    bot_name_proper = ui_display.display_bot_preview(bot_query)
    if bot_name_proper:
        last_viewed_bot = bot_name_proper

def handle_expand(cmd_line):
    """Handles the 'expand' command."""
    if len(cmd_line) < 2:
        print("Usage: expand <message_id>")
        return
    if not last_viewed_bot:
        print("--- Error: Use 'show <bot_name>' first to select a conversation. ---")
        return
    display_id = cmd_line[1]
    ui_display.display_full_message(last_viewed_bot, display_id)

def handle_chat(cmd_line):
    """Handles the 'chat' command with dual purpose."""
    global active_project
    if len(cmd_line) < 2:
        print("Usage: chat <bot_name>"); return

    bot_query = ' '.join(cmd_line[1:])
    bot_name = workspace_manager.find_bot_by_name_case_insensitive(bot_query)

    if bot_name: # Bot found in current workspace (active project or previously loaded single bot)
        prompt = input(f"Chatting with '{bot_name}': ")
        response = api_client.get_ai_response(bot_name, prompt)
        print(f"\n--- Response from {bot_name} ---\n{response}")
    elif active_project is None: # No bot in workspace, and no active project
        # Try to find it as a standalone bot in the 'projects' root directory
        filepath = os.path.join("projects", f"{bot_query}.json") # Assumes bot_query is the exact filename (no spaces)

        # We must make this content-aware like handle_load, so it supports "Hypothesis Engine" (no extension)
        found_bot_filepath = None
        for item in os.listdir("projects"):
            item_path = os.path.join("projects", item)
            if os.path.isfile(item_path):
                try:
                    with open(item_path, 'r', encoding='utf-8') as f: json.load(f)
                    if item.lower() == bot_query.lower() or item.replace('.json', '').lower() == bot_query.lower():
                        found_bot_filepath = item_path
                        break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

        if found_bot_filepath:
             # A standalone bot makes active_project None
            active_project = None
            workspace_manager.clear_workspace() # Clear any previous single bot
            loaded_name = workspace_manager.load_bot_from_json(found_bot_filepath, api_client.model)
            if loaded_name:
                print(f"Single bot '{loaded_name}' loaded for chat.")
                prompt = input(f"Chatting with '{loaded_name}': ")
                response = api_client.get_ai_response(loaded_name, prompt)
                print(f"\n--- Response from {loaded_name} ---\n{response}")
            else:
                print(f"Error: Could not load '{bot_query}'.")
        else:
            print(f"Error: Bot '{bot_query}' not found in current workspace or 'projects/' root.")
    else: # Bot not found in workspace, but there IS an active project
        print(f"Error: Bot '{bot_query}' not found in active project '{active_project}'.")
        print("Use 'project -> Add Existing Bot' to add it, or 'project -> Load Entire Project' to reload all bots.")

def handle_interactive_forward():
    """A guided wizard for the forward command."""
    global last_viewed_bot
    ui_display.clear_screen()
    print("--- Interactive Forward ---")
    
    origin_bot = None
    while True:
        origin_query = input("1. Enter name of ORIGIN bot (to forward FROM): ")
        origin_bot = workspace_manager.find_bot_by_name_case_insensitive(origin_query)
        if origin_bot:
            # Show the preview and update the last_viewed_bot
            last_viewed_bot = ui_display.display_bot_preview(origin_bot)
            break
        print(f"  Error: Bot '{origin_query}' not found. Try again.")

    msg_id = input(f"\n2. Enter Message ID from '{origin_bot}' to forward (e.g., A5): ")
    source_message = workspace_manager.find_message_by_display_id(origin_bot, msg_id)
    if not source_message:
        print(f"  Error: Message '{msg_id}' not found. Aborting."); return

    target_bot = None
    while True:
        target_query = input("3. Enter name of TARGET bot (to forward TO): ")
        target_bot = workspace_manager.find_bot_by_name_case_insensitive(target_query)
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

    response_text = api_client.get_ai_response(target_bot, final_prompt)
    print(f"\n--- Response from {target_bot} ---")
    print(response_text)
    print("-" * 60)

def handle_project_command():
    """The final, interactive hub for managing projects and their contents."""
    global active_project
    
    ui_display.clear_screen()
    title = f"--- Project Management [Active: {active_project if active_project else 'None'}] ---"
    print(title)
    print("1: Create New Bot (in active project)")
    print("2: Add Existing Bot (copy from another project)")
    print("3: List & Set Active Project") # <-- Wording updated for clarity
    print("0: Cancel / Go Back")
    print("-" * len(title))
    
    choice = input("Select an option: ")

    # --- Choice 1: Create New Bot ---
    if choice == '1':
        # This logic is already correct and complete from our previous work
        if not active_project:
            print("\nError: No active project. Please use option 3 to set one first."); return

        print("\nHow would you like to create this bot?")
        print("1: From a Template")
        print("2: From a New, Unique Prompt")
        print("0: Cancel")
        creation_choice = input("Select creation method: ")

        system_instruction = None
        if creation_choice == '1':
            template_dir = "templates"
            if not os.path.exists(template_dir) or not any(f.endswith(".txt") for f in os.listdir(template_dir)):
                 print("No templates found. Please create one first via the 'template' command."); return
            templates = [t for t in os.listdir(template_dir) if t.endswith(".txt")]
            print("\nSelect a template:")
            for i, t in enumerate(templates, 1):
                print(f"{i}: {t.replace('.txt', '').replace('_', ' ')}")
            
            try:
                template_choice_idx = int(input("Choose template: ")) - 1
                if 0 <= template_choice_idx < len(templates):
                    template_file = os.path.join(template_dir, templates[template_choice_idx])
                    with open(template_file, 'r', encoding='utf-8') as f:
                        system_instruction = f.read()
                else: raise ValueError
            except (ValueError, IndexError):
                print("Invalid template choice."); return

        elif creation_choice == '2':
            print("\nEnter the System Instruction. Press Enter on an empty line to save.")
            lines = []
            while True:
                line = input("> ")
                if not line: break
                lines.append(line)
            if lines: system_instruction = "\n".join(lines)
        
        else: return

        if not system_instruction:
            print("System instruction cannot be empty. Creation cancelled."); return
            
        bot_name = input("\nEnter a name for the new bot: ")
        if not bot_name: print("Bot name cannot be empty."); return

        workspace_manager.create_new_bot(active_project, bot_name, system_instruction, api_client.model)
        ui_display.display_workspace_status()

    # --- Choice 2: Add Existing Bot ---
    elif choice == '2':
        # This logic is also correct and complete
        if not active_project:
            print("\nError: No active project. Please use option 3 to set one first."); return
        
        all_bots = []
        for p_name in os.listdir("projects"):
            if p_name == active_project: continue
            p_path = os.path.join("projects", p_name)
            if os.path.isdir(p_path):
                for b_file in os.listdir(p_path):
                    if os.path.isfile(os.path.join(p_path, b_file)) and b_file.endswith(".json"):
                        all_bots.append({"project": p_name, "bot_file": b_file})
        
        if not all_bots:
            print("No other bots found in other projects to add."); return

        print("\nSelect a bot to copy into this project:")
        for i, b_info in enumerate(all_bots, 1):
            bot_display_name = b_info['bot_file'].replace('.json', '')
            print(f"{i}: [{b_info['project']}] -> {bot_display_name}")

        try:
            bot_choice_idx = int(input("Choose bot to copy: ")) - 1
            if 0 <= bot_choice_idx < len(all_bots):
                bot_to_copy = all_bots[bot_choice_idx]
                source_path = os.path.join("projects", bot_to_copy['project'], bot_to_copy['bot_file'])
                dest_path = os.path.join("projects", active_project, bot_to_copy['bot_file'])
                import shutil
                shutil.copy2(source_path, dest_path)
                print(f"Bot '{bot_to_copy['bot_file']}' copied to '{active_project}'.")
                workspace_manager.load_bot_from_json(dest_path, api_client.model)
                ui_display.display_workspace_status()
            else: raise ValueError
        except (ValueError, IndexError):
            print("Invalid bot choice.")

    # --- Choice 3: List & Set Active Project (NEW & IMPROVED) ---
    elif choice == '3':
        print("\nAvailable Projects:")
        projects_dir = "projects"
        if not os.path.exists(projects_dir): os.makedirs(projects_dir)
        projects = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
        
        if not projects:
            print("- No projects found. Use 'project' -> '1: Create New Bot' to start.")
            return

        for i, project_name in enumerate(projects, 1):
            print(f"{i}: {project_name}")
        print("0: Go Back")
            
        try:
            project_choice_idx = int(input("\nChoose project number to set as active (or 0 to go back): "))
            if project_choice_idx == 0: return

            if 1 <= project_choice_idx <= len(projects):
                project_name_dir = projects[project_choice_idx - 1]
                project_path = os.path.join(projects_dir, project_name_dir)

                active_project = project_name_dir
                workspace_manager.clear_workspace()

                bots_loaded = 0
                for bot_item in os.listdir(project_path):
                    filepath = os.path.join(project_path, bot_item)
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f: json.load(f)
                            workspace_manager.load_bot_from_json(filepath, api_client.model)
                            bots_loaded += 1
                        except (json.JSONDecodeError, UnicodeDecodeError): continue
                
                print(f"\nActive project set to '{active_project}' and loaded with {bots_loaded} bot(s).")
            else:
                raise ValueError
        except (ValueError, IndexError):
            print("Invalid project choice.")
            
    elif choice == '0': return
    else: print("Invalid option.")

def handle_template_command():
    """Handles template management via an interactive menu."""
    template_dir = "templates"
    if not os.path.isdir(template_dir):
        os.makedirs(template_dir) # Ensure it exists

    ui_display.clear_screen()
    print("--- Template Management ---")
    print("1: Create New Template")
    print("2: List All Templates")
    print("3: View Template Content")
    print("0: Cancel / Go Back")
    print("--------------------------")
    
    choice = input("Select an option: ")

    if choice == '1':
        template_name_raw = input("Enter new template name (e.g., Code Reviewer): ")
        if not template_name_raw: print("Name cannot be empty."); return
        template_name = template_name_raw.replace(' ', '_') + ".txt"
        filepath = os.path.join(template_dir, template_name)

        print("Enter the System Instruction for this template. Press Enter on an empty line to save.")
        lines = []
        while True:
            line = input("> ")
            if not line: break
            lines.append(line)
        
        if not lines: print("Template content cannot be empty."); return
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"Template '{template_name_raw}' created successfully.")

    elif choice == '2':
        print("\nAvailable Templates:")
        templates = [f for f in os.listdir(template_dir) if f.endswith(".txt")]
        if not templates: print("- No templates found.")
        for t in templates:
            # Show the user-friendly name without the extension
            print(f"- {t.replace('.txt', '').replace('_', ' ')}")
    
    elif choice == '3':
        template_name_raw = input("Enter template name to view: ")
        template_name = template_name_raw.replace(' ', '_') + ".txt"
        filepath = os.path.join(template_dir, template_name)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"\n--- Content of '{template_name_raw}' ---")
            print(content)
            print("----------------" + "-" * len(template_name_raw))
        except FileNotFoundError:
            print(f"Error: Template '{template_name_raw}' not found.")
    
    elif choice == '0': return
    else: print("Invalid option.")

def handle_delete_command():
    """Handles deletion of projects, bots, or templates via an interactive menu."""
    global active_project
    
    ui_display.clear_screen()
    print("--- Delete Asset ---")
    print("WARNING: This action is irreversible.")
    print("1: Delete a Project (and all its contents)")
    print("2: Delete a Bot (from the active project)")
    print("3: Delete a Template")
    print("0: Cancel")
    print("--------------------")

    choice = input("Select an option: ")

    if choice == '1': # Delete Project
        project_name_raw = input("Enter the name of the project to DELETE: ")
        project_name_dir = project_name_raw.replace(' ', '_')
        project_path = os.path.join("projects", project_name_dir)

        if not os.path.exists(project_path):
            print(f"Error: Project '{project_name_raw}' not found."); return
        if input(f"ARE YOU SURE you want to delete project '{project_name_raw}' and ALL its contents? (type 'yes' to confirm): ") != 'yes':
            print("Deletion cancelled."); return
        
        import shutil
        shutil.rmtree(project_path)
        if active_project == project_name_dir: # If deleted project was active, unset it
            active_project = None
            workspace_manager.clear_workspace()
        print(f"Project '{project_name_raw}' and its contents DELETED.")

    elif choice == '2': # Delete Bot (from active project)
        if not active_project:
            print("Error: No active project. Set one to delete a bot from it."); return
        
        project_path = os.path.join("projects", active_project)
        bots_in_project = [f for f in os.listdir(project_path) if f.endswith(".json") and os.path.isfile(os.path.join(project_path, f))]
        if not bots_in_project:
            print(f"No bots found in active project '{active_project}'."); return
        
        print("\nBots in current project:")
        for i, bot_file in enumerate(bots_in_project, 1):
            print(f"{i}: {bot_file.replace('.json', '')}")
        
        bot_choice = input("Select the number of the bot to DELETE: ")
        try:
            bot_idx = int(bot_choice) - 1
            if not 0 <= bot_idx < len(bots_in_project): raise ValueError
            
            bot_to_delete_file = bots_in_project[bot_idx]
            bot_to_delete_name = bot_to_delete_file.replace('.json', '')
            filepath = os.path.join(project_path, bot_to_delete_file)

            if input(f"ARE YOU SURE you want to delete bot '{bot_to_delete_name}' from '{active_project}'? (type 'yes' to confirm): ") != 'yes':
                print("Deletion cancelled."); return
            
            os.remove(filepath)
            # Remove from workspace if currently loaded
            if bot_to_delete_name in workspace_manager.workspace:
                del workspace_manager.workspace[bot_to_delete_name]
                del workspace_manager.chat_sessions[bot_to_delete_name]
            print(f"Bot '{bot_to_delete_name}' DELETED from project '{active_project}'.")
            ui_display.display_workspace_status() # Refresh status
        except (ValueError, IndexError):
            print("Invalid selection.")

    elif choice == '3': # Delete Template
        template_dir = "templates"
        templates = [f for f in os.listdir(template_dir) if f.endswith(".txt")]
        if not templates: print("No templates found to delete."); return
        
        print("\nAvailable Templates:")
        for i, t in enumerate(templates, 1):
            print(f"{i}: {t.replace('.txt', '').replace('_', ' ')}")
            
        template_choice = input("Select the number of the template to DELETE: ")
        try:
            template_idx = int(template_choice) - 1
            if not 0 <= template_idx < len(templates): raise ValueError
            
            template_to_delete_file = templates[template_idx]
            template_to_delete_name = template_to_delete_file.replace('.txt', '')
            filepath = os.path.join(template_dir, template_to_delete_file)

            if input(f"ARE YOU SURE you want to delete template '{template_to_delete_name}'? (type 'yes' to confirm): ") != 'yes':
                print("Deletion cancelled."); return
            
            os.remove(filepath)
            print(f"Template '{template_to_delete_name}' DELETED.")
        except (ValueError, IndexError):
            print("Invalid selection.")
            
    elif choice == '0': return
    else: print("Invalid option.")

# --- Main Application Loop ---
def run():
    """The main command handler loop."""
    # Initialize the AI model once at the start.
    api_client.initialize_api(API_KEY)
    
    ui_display.display_workspace_status()
    
    while True:

        # Dynamically set the prompt based on the active project
        prompt_prefix = f"(Aegis OS) [{active_project if active_project else 'No Project'}]> "

        print("\nCommands: [project] [template] [delete] [status] [show <bot>] [expand <id>] [forward] [chat <bot>] [exit]")
        cmd_line = input(prompt_prefix).strip().split()
        cmd = cmd_line[0].lower() if cmd_line else ""
        
        if cmd == "project":
            handle_project_command()
        elif cmd == "status":
            ui_display.display_workspace_status()
        elif cmd == "delete":
            handle_delete_command()
        elif cmd == "exit":
            print("Aegis OS shutdown. Session terminated.")
            break
        elif not cmd:
            continue
        elif cmd == "forward":
            handle_interactive_forward()
        elif cmd == "template":
            handle_template_command()
        elif cmd == "show":
            handle_show(cmd_line)
        elif cmd == "expand":
            handle_expand(cmd_line)
        elif cmd == "chat":
            handle_chat(cmd_line)
        else:
            print("Unknown command or missing arguments.")

if __name__ == "__main__":
    run()