# Jarvis Cortex 🧠
> **Portable Semantic Memory for Autonomous Agents**

Jarvis Cortex is a lightweight, local-first memory system designed to give AI agents "infinite" recall capabilities without heavy infrastructure.

## 🧠 How It Works (The Core Logic)

Unlike traditional keyword search (grep) or heavy vector databases (Pinecone/Milvus), Jarvis Cortex uses a **Hybrid Local Approach**:

### 1. Ingestion (Learning) 📥
- **Scanning:** The system scans your agent's memory files (markdown logs, daily journals).
- **Chunking:** It breaks long text into smaller, overlapping "chunks" (default: 1500 chars).
- **Embedding:** Each chunk is sent to an Embedding Model (e.g., Gemini `text-embedding-004`) which converts the text into a **Vector** (a list of 768 floating-point numbers representing the *meaning*).
- **Storage:** The text + vector are saved locally in a standard `SQLite` file (`cortex.db`). No external database servers required.

### 2. Retrieval (Remembering) 🔍
- **Query:** You ask a question (e.g., *"What did we decide about the API?"*).
- **Vector Search:** The system converts your question into a vector.
- **Math Magic:** It calculates the **Cosine Similarity** between your question's vector and every chunk in the database.
- **Result:** It returns the top chunks that are *semantically close* to your question, even if they don't share the exact same words.

### 3. Architecture 🏗️
- **Zero Infrastructure:** Just a Python script and a file.
- **Privacy First:** Your raw text stays on your machine. Only ephemeral vectors are computed via API.
- **Portable:** The entire brain is just one file (`cortex.db`). You can copy it to another server, and the agent instantly "knows" everything.

---

## ✨ Features

- **Lightweight:** Zero heavy dependencies (no Docker, no Postgres). Just Python + SQLite.
- **Portable:** Easy to copy/paste between agents. "Brain in a Box" architecture.
- **Semantic Search:** Finds information by meaning, not just keywords.
- **Cost-Effective:** Uses Google Gemini Embeddings (often free/cheap).
- **Privacy-First:** Your data stays local in `cortex.db`.

## 🚀 Installation

### Prerequisites
- Python 3.8+
- A Google Cloud API Key (with Gemini API access)

### 1. Clone the Repository
```bash
git clone https://github.com/orenluxy/jarvis-cortex.git ~/.openclaw/skills/jarvis-cortex
cd ~/.openclaw/skills/jarvis-cortex
```

### 2. Install Dependencies
Run the included helper script:
```bash
./install.sh
```
*Or manually:* `pip3 install google-generativeai numpy`

### 3. Configure API Key
Set your Google API key in your environment variables:
```bash
export GOOGLE_API_KEY="YOUR_ACTUAL_KEY_HERE"
```
*(You can also add this to your `.bashrc` or agent configuration file)*

## 📖 Usage

### Step 1: Ingest Memories (The Learning Phase)
Run this command to scan your memory files (default: `memory/*.md`) and build the brain:
```bash
./scripts/cortex.py ingest
```
*Tip: Run this periodically (e.g., daily via cron) to keep the brain updated.*

### Step 2: Recall Information (The Thinking Phase)
Ask the brain anything:
```bash
./scripts/cortex.py remember "What was the conclusion of the last security audit?"
```
**Output Example:**
```json
[
  {
    "score": 0.89,
    "content": "We decided to implement strict file permissions...",
    "source": "memory/2026-03-01.md",
    "date": "2026-03-01"
  }
]
```

### Step 3: Health Check
Verify the database status:
```bash
./scripts/cortex.py status
```

## 🛠️ Configuration
You can modify `scripts/cortex.py` to change defaults:
- `MEMORY_DIR`: Where your markdown files live (default: `"memory"`)
- `CHUNK_SIZE`: Text chunk size for embedding (default: `1500` chars)
- `EMBEDDING_MODEL`: Gemini model to use (default: `models/text-embedding-004`)

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
MIT License - Free to use and modify for your own agents.
