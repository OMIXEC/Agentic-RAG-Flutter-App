import requests
from openai import OpenAI

from .config import settings


def synthesize_answer(prompt: str) -> str:
    if settings.gemini_api_key:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
        }
        response = requests.post(url, json=body, timeout=60)
        if response.ok:
            payload = response.json()
            candidates = payload.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    text = part.get("text")
                    if text:
                        return text

    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You are a memory recall assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "I don't have enough info to answer."

    return "I don't have enough info to answer."
