# app.py
import chainlit as cl
from backend import RAGBackend

# Instantiate backend
backend = RAGBackend()

@cl.on_chat_start
async def start():
    # 1. Set the Assistant's Avatar (Name shown on every message)
    # This overrides the default "Assistant" name in the chat
    cl.user_session.set("author", "Luxomix Pro")

    # 2. Add a professional Welcome Banner
    # We use Markdown for clean UI/UX
    welcome_content = """
# ⚡ Luxomix Research Intelligence
Welcome to the official **GPT-5.2 Pro** demo environment. 

**Connected Systems:**
* **Vector DB:** Pinecone Serverless (3072-dim)
* **Knowledge Base:** Internal `.txt` & `.json` repository
* **Real-time Feed:** Luxomix Tech News 2026

*Type your query below to begin semantic retrieval.*
"""
    await cl.Message(content=welcome_content).send()

@cl.on_message
async def main(message: cl.Message):
    # Retrieve the custom author name
    author = cl.user_session.get("author")
    
    async with cl.Step(name="Luxomix Deep Search"):
        context, sources = backend.retrieve_context(message.content)

    # Initialize message with the custom author name
    msg = cl.Message(content="", author=author)
    
    # Generate the GPT-5.2 Pro response
    stream = backend.generate_answer(message.content, context)

    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        await msg.stream_token(token)

    # Add Source Citations footer
    if sources:
        msg.content += f"\n\n---\n**Sources used:** {', '.join(sources)}"
    
    await msg.send()

