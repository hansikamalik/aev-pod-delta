import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve API keys & settings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Active mode resolution
USE_GEMMA_GOOGLE = bool(GOOGLE_API_KEY)
USE_OPENAI = bool(OPENAI_API_KEY) and OPENAI_API_KEY != "sk-put-your-key-here"


def ask_gpt(question: str) -> str:
    """
    Send a question to AI model and return the answer.

    Priority:
    1. Gemma 4 via Google AI (FREE API) - if GOOGLE_API_KEY is set
    2. GPT-4o via OpenAI (PAID API)    - if OPENAI_API_KEY is set
    3. Mock response                   - if no key is set (for testing)
    """

    # ── MODE 1: GEMMA 4 via Google AI (FREE API) ───────────────────
    if USE_GEMMA_GOOGLE:
        from google import genai

        print(f"[GEMMA GOOGLE API MODE] Question received: {question}")

        client = genai.Client(api_key=GOOGLE_API_KEY)

        response = client.models.generate_content(
            model="gemma-4-31b-it",
            contents=question
        )

        return response.text

    # ── MODE 2: OPENAI (GPT-4o — PAID API) ─────────────────────────
    elif USE_OPENAI:
        import openai

        print(f"[OPENAI MODE] Question received: {question}")

        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant for an IT security platform."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            max_tokens=500
        )

        return response.choices[0].message.content

    # ── MODE 3: MOCK (Fallback — for local offline testing) ────────
    else:
        print(f"[MOCK MODE] Question received: {question}")
        return (
            f"[MOCK RESPONSE] Simulated answer to: '{question}'. "
            "Set GOOGLE_API_KEY in .env for free Gemma 4 responses."
        )
