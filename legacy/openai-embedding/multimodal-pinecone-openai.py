import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

# 1. HARD-CODED DIRECTORY SETUP
# Using the exact path you specified
DATA_DIR = Path("/Users/omixec/dev/github/Xheight-Projects/flutter-rag-demo/openai/data/txt")
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE, override=True)

# 2. CONFIGURATION
INDEX_NAME = "multimodal-embedding-demo-openai-3072"
MODEL_NAME = "text-embedding-3-large"
DIMENSIONS = 3072

# 3. INITIALIZE CLIENTS
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
index = pc.Index(INDEX_NAME)

def get_embedding(text: str):
    """Fetch 3072-dim vector from OpenAI."""
    # Clean text to prevent newline issues in embedding
    text = text.replace("\n", " ")
    return client.embeddings.create(
        input=[text], 
        model=MODEL_NAME, 
        dimensions=DIMENSIONS
    ).data[0].embedding

def load_text_data():
    """Ingests only .txt files from the specified folder."""
    if not DATA_DIR.exists():
        print(f"❌ Folder not found: {DATA_DIR}")
        return

    print(f"--- Starting Large Text Load (3072) ---")
    print(f"📁 Target Folder: {DATA_DIR}")
    
    upsert_batch = []
    
    # Target only .txt files in the specific subdirectory
    files = list(DATA_DIR.glob("*.txt"))
    if not files:
        print("⚠️ No .txt files found in the folder.")
        return

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content: continue
                
                print(f"📄 Embedding: {file_path.name}")
                vector = get_embedding(content)
                
                # Metadata stores text for display in your Flutter app later
                upsert_batch.append({
                    "id": f"txt_{file_path.name}",
                    "values": [float(v) for v in vector], # Float conversion for SDK stability
                    "metadata": {
                        "text": content[:3000], # Store preview in Pinecone
                        "source": file_path.name,
                        "modality": "text"
                    }
                })
        except Exception as e:
            print(f"❌ Failed to process {file_path.name}: {e}")

    # Upload to Pinecone
    if upsert_batch:
        index.upsert(vectors=upsert_batch)
        print(f"✅ Success! Loaded {len(upsert_batch)} files into {INDEX_NAME}")
    else:
        print("No valid text data to upload.")

def query_text(prompt: str):
    """Query logic for testing the index."""
    print(f"🔍 Searching: {prompt}")
    vector = get_embedding(prompt)
    
    results = index.query(
        vector=vector,
        top_k=3,
        include_metadata=True
    )
    
    for match in results['matches']:
        print(f"\n[Score: {match['score']:.3f}] Source: {match['metadata']['source']}")
        print(f"Snippet: {match['metadata']['text'][:300]}...")

if __name__ == '__main__':
    # Usage:
    # python script.py              -> Loads data
    # python script.py --query "X"  -> Searches data
    if "--query" in sys.argv or "-q" in sys.argv:
        query_val = sys.argv[-1]
        query_text(query_val)
    else:
        load_text_data()