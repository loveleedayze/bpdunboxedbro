import os
from pathlib import Path

import anthropic
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).parent
SYSTEM_PROMPT = (BASE_DIR / "system-prompt.md").read_text(encoding="utf-8")
MODEL = os.environ.get("BRO_MODEL", "claude-sonnet-5-5")
MAX_TURNS = 60  # keep long all-night conversations under the context limit

app = Flask(__name__, static_folder="static")
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

FALLBACK = (
    "I'm having trouble connecting right now, and I'm so sorry. "
    "If you're in immediate danger, please call your local emergency number, "
    "call or text 988 in the US or Canada, or find a free helpline for your "
    "country at findahelpline.com. Please try me again in a moment. 💜"
)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    messages = [
        {"role": m["role"], "content": str(m["content"])}
        for m in data.get("messages", [])
        if m.get("role") in ("user", "assistant") and m.get("content")
    ][-MAX_TURNS:]
    # The API requires the conversation to start with a user turn
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages:
        return jsonify({"response": FALLBACK}), 400

    try:
        result = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = "".join(b.text for b in result.content if b.type == "text")
        return jsonify({"response": reply or FALLBACK})
    except anthropic.APIError as e:
        app.logger.error("Anthropic API error: %s", e)
        return jsonify({"response": FALLBACK}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
