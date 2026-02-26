# backend.py
import os
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class RAGBackend:
    def __init__(self):
        # --- SPECIFIC MODEL SNAPSHOT ---
        self.chat_model = "gpt-5-mini-2025-08-07"
        self.embed_model = "text-embedding-3-large"
        self.dimensions = 3072

        # Clients
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.index = self.pc.Index("multimodal-embedding-demo-openai-3072")

    def retrieve_context(self, query: str, top_k=3):
        """Retrieve 3072-dim context from Pinecone."""
        xq = self.client.embeddings.create(
            input=[query.replace("\n", " ")],
            model=self.embed_model,
            dimensions=self.dimensions
        ).data[0].embedding
        
        res = self.index.query(vector=xq, top_k=top_k, include_metadata=True)
        contexts = [match['metadata']['text'] for match in res['matches']]
        sources = [match['metadata']['source'] for match in res['matches']]
        return "\n---\n".join(contexts), list(set(sources))

    def generate_answer(self, query: str, context: str):
        """
        Uses the gpt-5-mini-2025-08-07 snapshot.
        Note: GPT-5 series models use 'reasoning_effort' instead of temperature.
        """
        return self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": "You are the Luxomix AI Assistant. Use the provided context to answer."},
                {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {query}"}
            ],
            # GPT-5.x specific parameters
            # reasoning_effort can be: "none", "low", "medium", "high"
            extra_body={
                "reasoning_effort": "medium",
                "verbosity": "medium"
            },
            stream=True
        )

