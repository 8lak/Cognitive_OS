# Cognitive OS: A Multi-Agent AI Command-Line Workspace

**Status:** Version 0.1 (MVP) - Fully Functional Prototype

### Summary: "Cognitive OS" Prototype V5

This script is a powerful, proof-of-concept multi-agent AI workspace designed to run locally in your terminal. Its core purpose is to solve the problem of siloed AI conversations by enabling seamless context transfer between specialized AI "bots."

---

### The Genesis of this Project
This Cognitive OS was not born from a random idea, but from a practical necessity. While working on a deep, multi-disciplinary research project to model behavioral dynamics, I found that existing AI chat interfaces were insufficient. Managing separate, complex lines of inquiry in fields like Spectral Graph Theory, Reinforcement Learning, and Dynamical Systems became a major bottleneck.
I needed a tool that would allow me to orchestrate a team of specialized AI agents and facilitate seamless knowledge transfer between them. This workspace is the result of that need.
For those interested, the foundational research that prompted the creation of this tool can be viewed here:
[Read the Full Computational Framework Document](https://github.com/8lak/Complex_Systems_Modeling)

### Core Capabilities & User Features

*   **Multi-Agent Workspace:** Load multiple, distinct AI bots from AI Studio `.json` files, each with its own persistent conversation history.
*   **Rich & Forgiving UI:** Commands work with natural language, case-insensitive names. A clean, two-column view makes chats easy to scan, and any message can be instantly expanded.
*   **The "Killer Feature" - Interactive Forwarding:** A guided, step-by-step wizard makes forwarding context between bots simple, robust, and error-proof.
*   **Professional-Grade Responsiveness:** A non-blocking, asynchronous status indicator with a timer gives you complete confidence that the program is working during API calls.

*[Optional but HIGHLY Recommended: Insert a GIF here demonstrating the `forward` command in action. Tools like LiceCap or Kap make this easy.]*

---

### Technical Architecture

*   **Language:** Python 3 (requires virtual environment).
*   **AI Integration:** Leverages the Google Gemini 1.5 Flash model via the `google-generativeai` library.
*   **State Management:** Uses `start_chat()` to manage stateful conversations for each bot.
*   **Advanced Technique:** Employs Python's `threading` module for a non-blocking UI during API processing.
*   **Deep Dive:** For a full exploration of the systems-thinking philosophy behind this project, please see the [Computational Framework document](./docs/computational_framework.md).

---

### Setup & Installation

**1. Clone the Repository:**
```bash
git clone https://github.com/your-username/cognitive-os-mvp.git
cd cognitive-os-mvp
```

**2. Set Up Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**4. Configure Your API Key:**
   - Create a file named `.env` in the root directory.
   - Add your Google AI API key to it like this:
     ```
     API_KEY=your_actual_api_key_here
     ```

**5. Add Your Bots:**
   - Export your custom bots from Google AI Studio as `.json` files.
   - Place these `.json` files inside the `/bots` directory.

### How to Run

From the root directory, simply run the application:
```bash
python cognitive_os/app.py
```
Follow the on-screen commands. Type `help` to see a list of available commands.

---

### Future Roadmap

*   **V2:** Develop a UI using a web framework like Streamlit or Flask.
*   **V3:** Implement a database (e.g., SQLite) for more robust and scalable chat history management.
*   **V4:** Explore advanced context-passing, allowing for multiple messages or entire chat summaries to be forwarded.
