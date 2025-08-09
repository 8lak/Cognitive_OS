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

def handle_view_command():
    """A new stateful 'view mode' for inspecting and acting on the workspace."""
    global last_viewed_bot
    
    # This variable tracks the bot we are currently focused on within this mode
    currently_viewed_bot = None

    while True:
        ui_display.clear_screen()
        print("--- View & Inspect Mode ---")
        
        # Always show the high-level status
        status_data = workspace_manager.get_workspace_status()
        if not status_data:
            print("Workspace is empty. Use 'project' or 'chat' to load/create bots.")
        else:
            print("Currently Loaded Bots:")
            for bot_name, msg_count in status_data.items():
                # Highlight the currently focused bot
                prefix = ">>" if bot_name == currently_viewed_bot else "-"
                print(f"{prefix} {bot_name} ({msg_count} messages)")

        print("\n--- Commands ---")
        if not currently_viewed_bot:
            # Commands when no specific bot is being viewed
            print("[show <bot_name>] - Focus on a bot and see its preview")
            print("[exit]           - Return to the main menu")
        else:
            # Context-aware commands when a bot IS being viewed
            print(f"Viewing: {currently_viewed_bot}")
            print("[expand <id>]    - Show the full text of a message")
            print("[mforward]       - Start a multi-forward, using this bot as the first source")
            print("[unfocus]        - Return to the general bot list view")
            print("[exit]           - Return to the main menu")
        
        print("----------------")
        cmd_line = input("View Mode> ").strip().split()
        cmd = cmd_line[0].lower() if cmd_line else ""

        # --- Sub-command Logic ---
        if cmd == "exit":
            break # Exit the view mode loop

        elif cmd == "unfocus":
            currently_viewed_bot = None # Go back to the general view
            last_viewed_bot = None

        elif cmd == "show":
            if len(cmd_line) > 1:
                bot_query = ' '.join(cmd_line[1:])
                bot_name_proper = ui_display.display_bot_preview(bot_query)
                if bot_name_proper:
                    # Set the context for this mode
                    currently_viewed_bot = bot_name_proper
                    last_viewed_bot = bot_name_proper
            else:
                print("Usage: show <bot_name>")
                input("Press Enter to continue...")

        elif cmd == "expand":
            if not currently_viewed_bot:
                print("You must 'show' a bot before you can expand its messages.");
                input("Press Enter to continue..."); continue
            if len(cmd_line) > 1:
                display_id = cmd_line[1]
                # Now we need a way to forward FROM the expanded view
                ui_display.display_full_message(currently_viewed_bot, display_id)
                
                # --- NEW: Action Sub-menu after expanding ---
                print("\nActions for this message:")
                print("1: Forward this message (start mforward)")
                print("0: Return to View Mode")
                action_choice = input("Select action: ")
                if action_choice == '1':
                    # Pre-load the mforward payload with this message
                    handle_mforward_with_initial_context(currently_viewed_bot, display_id)
            else:
                print("Usage: expand <id>")
                input("Press Enter to continue...")

        elif cmd == "mforward":
            if not currently_viewed_bot:
                print("You must 'show' a bot to use it as the first source.");
                input("Press Enter to continue..."); continue
            
            # Start the mforward process, pre-loading the first bot
            handle_mforward_with_initial_context(currently_viewed_bot)

        else:
            print("Unknown command for View Mode.")
            input("Press Enter to continue...")

def handle_chat():
    """Dual-purpose handler for all direct bot interaction."""
    global active_project, last_viewed_bot

    # --- MODE 1: A project IS active ---
    if active_project:
        bots_in_project = list(workspace_manager.get_workspace_status().keys())
        if not bots_in_project:
            print(f"No bots loaded in project '{active_project}'. Use 'project' menu to create or add one."); return

        print(f"\nSelect a bot to chat with in project '{active_project}':")
        for i, bot_name in enumerate(bots_in_project, 1):
            print(f"{i}: {bot_name}")
        
        try:
            choice_idx = int(input("Choose bot: ")) - 1
            if 0 <= choice_idx < len(bots_in_project):
                bot_to_chat = bots_in_project[choice_idx]
                last_viewed_bot = bot_to_chat
                prompt = input(f"Chatting with '{bot_to_chat}': ")
                response = api_client.get_ai_response(bot_to_chat, prompt)
                print(f"\n--- Response from {bot_to_chat} ---\n{response}")
            else: raise ValueError
        except (ValueError, IndexError):
            print("Invalid choice."); return

    # --- MODE 2: NO project is active (Single Bot Mode) ---
    else:
        ui_display.clear_screen()
        print("--- Single Bot Mode ---")
        print("1: Chat with an Existing Standalone Bot")
        print("2: Create a New Standalone Bot")
        print("0: Go Back")
        choice = input("Select an option: ")

        if choice == '1': # Chat with Existing
            standalone_bots = []
            for item in os.listdir("projects"):
                item_path = os.path.join("projects", item)
                if os.path.isfile(item_path):
                    try:
                        with open(item_path, 'r', encoding='utf-8') as f: json.load(f)
                        standalone_bots.append(item)
                    except (json.JSONDecodeError, UnicodeDecodeError): continue
            
            if not standalone_bots:
                print("No standalone bot files found in '/projects' root."); return
            
            print("\nSelect a standalone bot to load and chat with:")
            for i, bot_file in enumerate(standalone_bots, 1):
                print(f"{i}: {bot_file.replace('.json', '') if bot_file.endswith('.json') else bot_file}")
            
            try:
                bot_choice_idx = int(input("Choose bot: ")) - 1
                if 0 <= bot_choice_idx < len(standalone_bots):
                    filepath = os.path.join("projects", standalone_bots[bot_choice_idx])
                    workspace_manager.clear_workspace()
                    loaded_name = workspace_manager.load_bot_from_json(filepath, api_client.model)
                    if loaded_name:
                        last_viewed_bot = loaded_name
                        prompt = input(f"Chatting with '{loaded_name}': ")
                        response = api_client.get_ai_response(loaded_name, prompt)
                        print(f"\n--- Response from {loaded_name} ---\n{response}")
                else: raise ValueError
            except (ValueError, IndexError):
                print("Invalid choice."); return
        
        elif choice == '2': # Create New Standalone Bot
            print("\nHow would you like to create this bot's persona?")
            print("1: From a Template")
            print("2: From a New, Unique Prompt")
            print("3. Co-author with Prompter Bot")
            creation_choice = input("Select method: ")
            
            system_instruction = None
            if creation_choice == '1': # From Template
                # This logic can be copied/refactored from handle_project_command
                # For brevity, this is a placeholder for that logic
                print("Loading from template...")
                # ... full template selection logic here ...
            elif creation_choice == '2': # New Prompt
                print("\nEnter the System Instruction. Press Enter on an empty line to save.")
                lines = []
                lines = []
                while True:
                    line = input("> ")
                    if not line:
                        if lines:
                            system_instruction = "\n".join(lines)
                        break
                    lines.append(line)
            elif creation_choice == '3': # Prompter Bot
                system_instruction = api_client.launch_prompter_bot_session()

            if system_instruction:
                bot_name = input("\nEnter a name for the new standalone bot: ")
                if bot_name:
                    workspace_manager.create_standalone_bot(bot_name, system_instruction, api_client.model)
                    ui_display.display_workspace_status()
                else: print("Bot name cannot be empty.")
            else: print("System instruction cannot be empty. Creation cancelled.")

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
        print("3. Co-author with Prompter Bot")
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

        elif creation_choice == '3': # Co-author with Prompter Bot
            system_instruction = api_client.launch_prompter_bot_session()
    
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
                save_current_workspace_state()
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

        print("\nHow would you like to create this template's content?")
        print("1: Write it manually")
        print("2: Co-author with Prompter Bot")
        template_creation_choice = input("Select method: ")

        if template_creation_choice == '1':
            print("Enter the System Instruction for this template. Press Enter on an empty line to save.")
            lines = []
            while True:
                line = input("> ")
                if not line: break
                lines.append(line)
        elif template_creation_choice == '2':
            lines = [api_client.launch_prompter_bot_session()]
        
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
    
    elif choice == '3': # List & View Template Content
        print("\nAvailable Templates:")
        templates = [f for f in os.listdir(template_dir) if f.endswith(".txt")]
        if not templates: print("- No templates found."); return

        for i, t in enumerate(templates, 1):
            print(f"{i}: {t.replace('.txt', '').replace('_', ' ')}")
        print("0: Go Back")
            
        try:
            template_choice_idx = int(input("\nChoose template number to view its content: "))
            if template_choice_idx == 0: return

            if 1 <= template_choice_idx <= len(templates):
                template_file = os.path.join(template_dir, templates[template_choice_idx - 1])
                template_name_raw = templates[template_choice_idx - 1].replace('.txt', '').replace('_', ' ')
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"\n--- Content of '{template_name_raw}' ---")
                print(content)
                print("----------------" + "-" * len(template_name_raw))
            else:
                raise ValueError
        except (ValueError, IndexError):
            print("Invalid template choice.")

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

def save_current_workspace_state():
    """A helper function to save the state of all bots in the active project."""
    if not active_project:
        return # Nothing to save if no project is active

    print(f"\nSaving workspace state for project '{active_project}'...")
    
    # Get the list of all bots currently loaded in the workspace
    loaded_bots = workspace_manager.get_workspace_status().keys()
    
    saved_count = 0
    for bot_name in loaded_bots:
        if workspace_manager.save_bot_state(active_project, bot_name):
            saved_count += 1
            
    print(f"Saved {saved_count} bot(s) successfully.")

def handle_mforward_with_initial_context(first_bot=None, first_msg_id=None):
    """
    Handles MCF, optionally pre-loaded with initial context from the view mode.
    """
    global last_viewed_bot
    mcf_payload = []

    ui_display.clear_screen()
    print("--- Multi-Context Forward (MCF) ---")
    
    # --- Pre-load initial context if provided ---
    if first_bot and first_msg_id:
        source_message = workspace_manager.find_message_by_display_id(first_bot, first_msg_id)
        if source_message:
            source_content = source_message.get("parts", [""])[0]
            context_snippet = (
                f"--- CONTEXT from '{first_bot}' (msg {first_msg_id}) ---\n"
                f"{source_content}\n"
                f"--- END CONTEXT ---\n"
            )
            mcf_payload.append(context_snippet)
            print(f"Pre-loaded context from {first_bot}:{first_msg_id} into payload.")

    # --- The Context Aggregation Loop ---
    while True:
        print(f"\nPayload contains {len(mcf_payload)} item(s).")
        print("1: Add Context from a Bot")
        print("2: Finish and Send Payload")
        print("0: Cancel")
        choice = input("Select an option: ")

        if choice == '0':
            print("MCF cancelled."); return
        
        if choice == '2': # Finish and Send
            if not mcf_payload:
                print("Payload is empty. Add at least one context item first."); continue
            else:
                break # Exit the loop to proceed to targeting

        if choice == '1': # Add Context
            origin_bot_name = None
            while True:
                origin_query = input("\nEnter name of a SOURCE bot (or type 'list'): ")
                if origin_query.lower() == 'list':
                    ui_display.display_workspace_status(); continue
                
                origin_bot_name = workspace_manager.find_bot_by_name_case_insensitive(origin_query)
                if origin_bot_name:
                    last_viewed_bot = ui_display.display_bot_preview(origin_bot_name)
                    break
                else:
                    print(f"  Error: Bot '{origin_query}' not found.")
            
            print(f"\nSelect context type for '{origin_bot_name}':")
            print("1: Single Message (by ID)")
            print("2: Just-In-Time (JIT) Summary (you provide a prompt)")
            context_type_choice = input("Choose context type: ")

            # --- RESTRUCTURED LOGIC ---
            
            if context_type_choice == '1': # Single Message
                msg_id = input(f"\nEnter Message ID from '{origin_bot_name}' to add: ")
                source_message = workspace_manager.find_message_by_display_id(origin_bot_name, msg_id)
                
                if source_message:
                    source_content = source_message.get("parts", [""])[0]
                    context_snippet = (
                        f"--- CONTEXT from '{origin_bot_name}' (msg {msg_id}) ---\n"
                        f"{source_content}\n"
                        f"--- END CONTEXT ---\n"
                    )
                    mcf_payload.append(context_snippet)
                    print(f"Successfully added context from {origin_bot_name}:{msg_id} to payload.")
                else:
                    print(f"  Error: Message '{msg_id}' not found.")

            elif context_type_choice == '2': # JIT Summary
                print("\nHow would you like to write the JIT prompt?")
                print("1: Write it manually")
                print("2: Co-author with Prompter Bot")
                jit_prompt_choice = input("Select method: ")
                    
                jit_prompt = None
                if jit_prompt_choice == '1':
                    jit_prompt = input(f"\nEnter your one-off prompt for '{origin_bot_name}': ")
                elif jit_prompt_choice == '2':
                        jit_prompt = api_client.launch_prompter_bot_session()
                if not jit_prompt:
                    print("JIT prompt cannot be empty."); continue
                
                jit_summary = api_client.get_onetime_response(origin_bot_name, jit_prompt)
                
                if jit_summary:
                    context_snippet = (
                        f"--- JIT SUMMARY from '{origin_bot_name}' ---\n"
                        f"User Prompt: '{jit_prompt}'\n"
                        f"Response: {jit_summary}\n"
                        f"--- END SUMMARY ---\n"
                    )
                    mcf_payload.append(context_snippet)
                    print(f"Successfully added JIT summary from '{origin_bot_name}' to payload.")
                else:
                    print("Failed to generate JIT summary.")
            
            else:
                print("Invalid context type choice.")

            

    # --- Targeting and Execution ---
    ui_display.clear_screen()
    print("--- Sending MCF Payload ---")
    print(f"Payload contains {len(mcf_payload)} context items.")
    
    target_bot_name = None
    while True:
        target_query = input("\nEnter name of the TARGET bot to receive this payload: ")
        target_bot_name = workspace_manager.find_bot_by_name_case_insensitive(target_query)
        if target_bot_name:
            break
        else:
            print(f"  Error: Target bot '{target_query}' not found.")
            
    final_user_prompt = input(f"\nEnter the final prompt/task for '{target_bot_name}': ")

    # Assemble the final prompt
    final_prompt = "I am providing you with an aggregated payload of context from multiple sources.\n\n"
    final_prompt += "\n".join(mcf_payload)
    final_prompt += f"\nBased on all the context provided above, here is your task:\n{final_user_prompt}"

    # Send it to the AI
    response_text = api_client.get_ai_response(target_bot_name, final_prompt)
    print(f"\n--- Response from {target_bot_name} ---")
    print(response_text)
    print("-" * 60)
# --- Main Application Loop ---
def run():
    """The main command handler loop."""
    # Initialize the AI model once at the start.
    api_client.initialize_api(API_KEY)
    
    ui_display.display_workspace_status()
    
    while True:

        # Dynamically set the prompt based on the active project
        prompt_prefix = f"(Aegis OS) [{active_project if active_project else 'No Project'}]> "

        print("\nCommands: [chat] [project] [template] [delete] [view] [mforward] [exit]")
        cmd_line = input(prompt_prefix).strip().split()
        cmd = cmd_line[0].lower() if cmd_line else ""
        
        if cmd == "project":
            handle_project_command()
        elif cmd == "status":
            ui_display.display_workspace_status()
        elif cmd == "delete":
            handle_delete_command()
        elif cmd == "exit":
            save_current_workspace_state()
            print("Aegis OS shutdown. Session terminated.")
            break
        elif not cmd:
            continue
        elif cmd == "mforward": 
            handle_mforward_with_initial_context()
        elif cmd == "template":
            handle_template_command()
        elif cmd == "view":       
            handle_view_command()
        elif cmd == "chat":
            handle_chat()
        else:
            print("Unknown command or missing arguments.")

if __name__ == "__main__":
    run()