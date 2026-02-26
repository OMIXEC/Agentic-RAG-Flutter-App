import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

# 1. SETUP
DATA_DIR = Path("/Users/omixec/dev/github/Xheight-Projects/flutter-rag-demo/openai/data/txt")
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE, override=True)

# 2. CONFIG
INDEX_NAME = "multimodal-embedding-demo-openai-3072"
MODEL_NAME = "text-embedding-3-large"
DIMENSIONS = 3072

# 3. CLIENTS
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
index = pc.Index(INDEX_NAME)

def get_embedding(text: str):
    return client.embeddings.create(
        input=[text.replace("\n", " ")], 
        model=MODEL_NAME, 
        dimensions=DIMENSIONS
    ).data[0].embedding

def load_data():
    print(f"--- Scanning Folder: {DATA_DIR} ---")
    
    # FOR loop using scandir to catch EVERYTHING
    found_files = 0
    for entry in os.scandir(DATA_DIR):
        if entry.is_file() and entry.name.lower().endswith(".txt"):
            found_files += 1
            file_id = f"file_{entry.name}"

            # CHECK: Does this ID exist?
            # We use fetch to avoid re-embedding
            existing = index.fetch(ids=[file_id])
            if existing and file_id in existing.get('vectors', {}):
                print(f"⏩ Already Stored: {entry.name}")
                continue

            try:
                print(f"⚙️  New File Found! Embedding: {entry.name}...")
                with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    if not content: continue
                    
                    vector = get_embedding(content)
                    index.upsert(vectors=[{
                        "id": file_id,
                        "values": [float(v) for v in vector],
                        "metadata": {"text": content[:5000], "source": entry.name}
                    }])
                    print(f"✅ Stored: {entry.name}")
            except Exception as e:
                print(f"❌ Error with {entry.name}: {e}")
    
    if found_files == 0:
        print("⚠️ No .txt files found. Check your path or extensions.")
    else:
        print(f"--- Finished Scanning {found_files} files ---")

def interactive_query():
    # WHILE loop to allow continuous testing
    print("\n--- Interactive Search Mode ---")
    while True:
        query = input("\nEnter search (or 'exit' to quit): ").strip()
        if query.lower() in ['exit', 'quit', 'q']:
            break
        
        print(f"🔍 Searching for: {query}")
        vector = get_embedding(query)
        res = index.query(vector=vector, top_k=2, include_metadata=True)
        
        for match in res['matches']:
            print(f" >> [{match['score']:.3f}] {match['metadata']['source']}")

if __name__ == '__main__':
    # Step 1: Ingest all files in the folder
    load_data()
    
    # Step 2: Enter query loop if requested
    if "--query" in sys.argv:
        interactive_query()