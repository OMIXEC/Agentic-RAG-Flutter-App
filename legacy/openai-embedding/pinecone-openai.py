import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

# Setup Paths
ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(__file__).resolve().with_name('.env')
load_dotenv(ENV_FILE, override=True)

# Configuration
INDEX_NAME = "multimodal-embedding-demo-openai-3072"
MODEL_NAME = "text-embedding-3-large"
DIMENSIONS = 3072
DATA_DIR = ROOT / "data"

# Initialize Clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
index = pc.Index(INDEX_NAME)

def get_embedding(text: str):
    """Fetch 3072-dim embedding from OpenAI."""
    text = text.replace("\n", " ")
    return client.embeddings.create(
        input=[text], 
        model=MODEL_NAME, 
        dimensions=DIMENSIONS
    ).data[0].embedding

def load_and_embed():
    """Scan the data/ folder and upload text files to Pinecone."""
    if not DATA_DIR.exists():
        print(f"❌ Error: {DATA_DIR} does not exist.")
        return

    print(f"--- Starting 3072 Large Text Load ---")
    print(f"📁 Source: {DATA_DIR}")
    
    upsert_data = []
    
    # Process only text files
    for file_path in DATA_DIR.glob("*.txt"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    continue
                
                print(f"📄 Embedding: {file_path.name}...")
                vector = get_embedding(content)
                
                # Create a unique ID and store original text in metadata
                upsert_data.append({
                    "id": file_path.name,
                    "values": [float(x) for x in vector], # Ensure float32 compatibility
                    "metadata": {
                        "text": content[:1000], # Store preview
                        "source": file_path.name,
                        "type": "text"
                    }
                })
        except Exception as e:
            print(f"⚠️ Failed to process {file_path.name}: {e}")

    # Upsert to Pinecone
    if upsert_data:
        index.upsert(vectors=upsert_data)
        print(f"✅ Successfully loaded {len(upsert_data)} files into {INDEX_NAME}")
    else:
        print("Empty data folder or no .txt files found.")

def query_rag(prompt: str):
    """Standard RAG query logic."""
    print(f"🔍 Querying: {prompt}")
    query_vector = get_embedding(prompt)
    
    results = index.query(
        vector=query_vector,
        top_k=3,
        include_metadata=True
    )
    
    for match in results['matches']:
        print(f"\n[Score: {match['score']:.4f}] {match['id']}")
        print(f"Snippet: {match['metadata']['text'][:200]}...")

if __name__ == '__main__':
    # Usage: python script.py --query "your question" 
    # Or just: python script.py to load data
    if "--query" in sys.argv or "-q" in sys.argv:
        query_text = sys.argv[-1]
        query_rag(query_text)
    else:
        load_and_embed()

