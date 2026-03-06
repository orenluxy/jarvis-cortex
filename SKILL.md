# Jarvis Cortex (Portable Semantic Memory)

## 📦 What is this?
A lightweight, portable semantic memory system ("Brain in a Box").
It ingests your agent's markdown memory files (`MEMORY.md`, `memory/*.md`) into a local SQLite vector database (`cortex.db`).
It allows you to "recall" information using natural language, finding relevant facts even if the exact keywords don't match.

## 🚀 Installation (How to Transfer)
To install this skill on **any other agent** (e.g., `galad`, `shishi`):

1.  **Copy the folder:**
    Copy the entire `jarvis-cortex` folder to the target agent's skill directory.
    ```bash
    cp -r /root/clawd/skills/jarvis-cortex /root/galad/skills/
    ```

2.  **Install Dependencies:**
    Run the install script inside the target agent's folder.
    ```bash
    cd /root/galad/skills/jarvis-cortex
    ./install.sh
    ```

3.  **Configure API Key:**
    Ensure the target agent has `GOOGLE_API_KEY` set in its environment or `config.json`.

## 🛠️ Usage

### Ingest (Learn)
Scans your memory files and updates the brain. Run this periodically or after major events.
```bash
./scripts/cortex.py ingest
```

### Remember (Recall)
Ask the brain a question to find relevant memories.
```bash
./scripts/cortex.py remember "What did we decide about the API structure?"
```

### Status
Check the brain's health.
```bash
./scripts/cortex.py status
```

## ⚙️ Technical Details
- **Storage:** Local SQLite (`cortex.db`). No servers, no Docker.
- **Embeddings:** Google Gemini (`text-embedding-004`).
- **Logic:** Python 3 (simple script, no heavy frameworks).
- **Privacy:** Data stays local (except for the embedding API call).
