#!/usr/bin/env python3
"""
Jarvis Cortex (Lite) - Portable Semantic Memory
Designed to be easily transferable between agents.
Uses Gemini API for embeddings, stores in local SQLite.
"""
import os
import sys
import sqlite3
import json
import time
import glob
import hashlib
import numpy as np
import google.generativeai as genai
from typing import List, Dict

# --- Configuration ---
# Use relative paths for portability
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Database file is stored one level up from scripts/ (in the skill root)
DB_PATH = os.path.join(SCRIPT_DIR, "../cortex.db")
MEMORY_DIR = "memory"
API_KEY_ENV = "GOOGLE_API_KEY"
EMBEDDING_MODEL = "models/text-embedding-004"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 100

def get_api_key():
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        # Try to find config.json in parent directories
        current_dir = os.getcwd()
        paths_to_check = [
            os.path.join(current_dir, "config.json"),
            os.path.join(current_dir, "../config.json"),
            os.path.join(os.path.expanduser("~/.openclaw/config.json"))
        ]
        for path in paths_to_check:
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        config = json.load(f)
                        # Check various common keys
                        api_key = config.get("gemini_api_key") or config.get("google_api_key")
                        if api_key: break
            except:
                pass
                
    if not api_key:
        # Return None instead of exiting, so status check can run
        return None
    return api_key

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge
                 (id TEXT PRIMARY KEY, content TEXT, embedding BLOB, source TEXT, updated_at REAL)''')
    conn.commit()
    return conn

def get_embedding(text: str, task_type: str) -> List[float]:
    try:
        # Try the newer model first
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type=task_type
        )
        return result['embedding']
    except Exception as e:
        # Fallback to older model if 004 fails or 404s
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type=task_type
            )
            return result['embedding']
        except Exception as e2:
            # print(f"Error generating embedding: {e2}", file=sys.stderr)
            return []

def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + size, text_len)
        if end < text_len:
            # Find last newline/period to break cleanly
            for delimiter in ["\n\n", "\n", ". "]:
                idx = text.rfind(delimiter, start, end)
                if idx != -1:
                    end = idx + len(delimiter)
                    break
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def ingest_file(conn, file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return 0

    file_mtime = os.path.getmtime(file_path)
    chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
    c = conn.cursor()
    c.execute("DELETE FROM knowledge WHERE source = ?", (file_path,))
    
    count = 0
    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        
        embedding = get_embedding(chunk, "retrieval_document")
        if not embedding:
            time.sleep(1.0) # Backoff
            continue
            
        chunk_id = hashlib.md5(f"{file_path}_{i}_{file_mtime}".encode()).hexdigest()
        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
        
        c.execute("INSERT INTO knowledge (id, content, embedding, source, updated_at) VALUES (?, ?, ?, ?, ?)",
                  (chunk_id, chunk, embedding_blob, file_path, file_mtime))
        count += 1
        time.sleep(0.5) # Rate limit friendly
        
    conn.commit()
    return count

def ingest_all(conn, force=False):
    # Only ingest MEMORY.md and recent daily logs to keep it fast
    files = glob.glob("MEMORY.md")
    files.extend(glob.glob("memory/daily/*/*.md")) # Daily logs nested
    files.extend(glob.glob("memory/*.md")) # Root memory logs
    
    # Sort by time, take most recent 20 files to avoid timeout on huge ingestion
    files.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)
    files = [f for f in files if os.path.exists(f)][:20]

    total_chunks = 0
    for file_path in files:
        file_mtime = os.path.getmtime(file_path)
        if not force:
            c = conn.cursor()
            c.execute("SELECT updated_at FROM knowledge WHERE source = ? LIMIT 1", (file_path,))
            row = c.fetchone()
            if row and abs(row[0] - file_mtime) < 1.0:
                continue
                
        total_chunks += ingest_file(conn, file_path)
        
    return total_chunks

def search(conn, query: str, limit: int = 5):
    query_vec = get_embedding(query, "retrieval_query")
    if not query_vec: return []
    
    query_vec_np = np.array(query_vec, dtype=np.float32)
    c = conn.cursor()
    c.execute("SELECT content, embedding, source, updated_at FROM knowledge")
    rows = c.fetchall()
    
    results = []
    for content, emb_blob, source, updated_at in rows:
        emb_np = np.frombuffer(emb_blob, dtype=np.float32)
        # Cosine similarity
        norm_q = np.linalg.norm(query_vec_np)
        norm_e = np.linalg.norm(emb_np)
        if norm_q == 0 or norm_e == 0:
            similarity = 0
        else:
            similarity = np.dot(query_vec_np, emb_np) / (norm_q * norm_e)
            
        results.append((similarity, content, source, updated_at))
        
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:limit]

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: cortex.py [ingest|remember|status]"})); sys.exit(1)
    
    api_key = get_api_key()
    conn = init_db()
    command = sys.argv[1]
    
    try:
        if command == "status":
            c = conn.cursor()
            c.execute("SELECT COUNT(*), COUNT(DISTINCT source) FROM knowledge")
            row = c.fetchone()
            print(json.dumps({
                "total_chunks": row[0], 
                "total_files": row[1], 
                "db_path": DB_PATH,
                "api_key_configured": bool(api_key)
            }))
            return

        # Commands below require API Key
        if not api_key:
            print(json.dumps({"error": f"API Key not found. Set {API_KEY_ENV}."})); sys.exit(1)
            
        genai.configure(api_key=api_key)

        if command == "ingest":
            force = "--force" in sys.argv
            target = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--force" else None
            
            if target:
                count = ingest_file(conn, target)
                print(json.dumps({"status": "success", "message": f"Ingested {target} ({count} chunks)"}))
            else:
                count = ingest_all(conn, force)
                print(json.dumps({"status": "success", "message": f"Ingested {count} chunks from recent files"}))
                
        elif command == "remember":
            query = " ".join(sys.argv[2:])
            results = search(conn, query)
            output = []
            for r in results:
                date_str = "Unknown"
                try:
                    date_str = time.strftime('%Y-%m-%d', time.localtime(r[3]))
                except: pass
                output.append({
                    "score": float(r[0]), 
                    "content": r[1], 
                    "source": r[2], 
                    "date": date_str
                })
            print(json.dumps(output, indent=2))
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))
    finally:
        conn.close()

if __name__ == "__main__":
    main()
