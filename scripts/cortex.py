#!/usr/bin/env python3
import os
import sqlite3
import json
import argparse
import time
import requests
import numpy as np
import datetime
from pathlib import Path
from typing import List, Dict, Any

# --- CONFIGURATION ---
DB_PATH = "cortex.db"
MEMORY_DIR = "memory"
CHUNK_SIZE = 1500
EMBEDDING_MODEL = "models/text-embedding-004"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS memories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT,
                  source TEXT,
                  date TEXT,
                  embedding BLOB)''')
    conn.commit()
    return conn

# --- EMBEDDING FUNCTIONS (LIGHTWEIGHT REST) ---
def get_embedding_google(text: str) -> List[float]:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/{EMBEDDING_MODEL}:embedContent?key={GOOGLE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": EMBEDDING_MODEL,
        "content": {"parts": [{"text": text}]}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result["embedding"]["values"]
    except Exception as e:
        print(f"❌ Google Embedding Error: {e}")
        return []

def get_embedding_openai(text: str) -> List[float]:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")
    
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as e:
        print(f"❌ OpenAI Embedding Error: {e}")
        return []

def get_embedding(text: str) -> List[float]:
    # Priority: Google (Free) > OpenAI (Paid)
    if GOOGLE_API_KEY:
        return get_embedding_google(text)
    elif OPENAI_API_KEY:
        return get_embedding_openai(text)
    else:
        raise ValueError("No API Key found! Set GOOGLE_API_KEY or OPENAI_API_KEY.")

# --- INGESTION ---
def chunk_text(text: str, size: int) -> List[str]:
    return [text[i:i+size] for i in range(0, len(text), size)]

def ingest(conn):
    print(f"📂 Scanning {MEMORY_DIR}...")
    files = list(Path(MEMORY_DIR).glob("*.md"))
    
    count = 0
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Check if already indexed (simple check by source)
        c = conn.cursor()
        c.execute("SELECT id FROM memories WHERE source = ?", (str(file_path),))
        if c.fetchone():
            continue
            
        chunks = chunk_text(content, CHUNK_SIZE)
        for chunk in chunks:
            if not chunk.strip(): continue
            
            vector = get_embedding(chunk)
            if not vector: continue
            
            # Pack vector as binary blob for SQLite
            blob = np.array(vector, dtype=np.float32).tobytes()
            
            today = datetime.date.today().isoformat()
            c.execute("INSERT INTO memories (content, source, date, embedding) VALUES (?, ?, ?, ?)",
                      (chunk, str(file_path), today, blob))
            count += 1
            print(f"✅ Indexed chunk from {file_path}")
            
            # Rate limit protection (free tier)
            time.sleep(1) 
            
    conn.commit()
    print(f"🎉 Ingestion complete! Added {count} new memories.")

# --- RETRIEVAL ---
def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def remember(conn, query: str, limit: int = 3):
    query_vec = get_embedding(query)
    if not query_vec: return []
    
    q_vec = np.array(query_vec, dtype=np.float32)
    
    c = conn.cursor()
    c.execute("SELECT content, source, date, embedding FROM memories")
    rows = c.fetchall()
    
    results = []
    for row in rows:
        content, source, date, blob = row
        mem_vec = np.frombuffer(blob, dtype=np.float32)
        
        score = cosine_similarity(q_vec, mem_vec)
        if score > 0.4: # Threshold
            results.append({
                "score": float(score),
                "content": content,
                "source": source,
                "date": date
            })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis Cortex Memory System")
    subparsers = parser.add_subparsers(dest="command")
    
    ingest_parser = subparsers.add_parser("ingest", help="Ingest memory files")
    
    remember_parser = subparsers.add_parser("remember", help="Recall information")
    remember_parser.add_argument("query", type=str, help="What do you want to remember?")
    
    status_parser = subparsers.add_parser("status", help="Check database status")

    args = parser.parse_args()
    
    conn = init_db()
    
    if args.command == "ingest":
        ingest(conn)
    elif args.command == "remember":
        results = remember(conn, args.query)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.command == "status":
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM memories")
        count = c.fetchone()[0]
        print(f"🧠 Cortex Status: Online")
        print(f"📚 Total Memories: {count}")
        print(f"📂 Database Size: {os.path.getsize(DB_PATH) / 1024:.2f} KB")
    else:
        parser.print_help()
        
    conn.close()
