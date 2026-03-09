# Ad LLM — Backend Orchestrator

FastAPI backend for the Ad LLM conversational ad platform.

## Quick Start

### 1. Start infrastructure

```bash
docker compose up -d
```

This spins up Postgres (with pgvector) and Redis locally.

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate # source .venv/Scripts/activate 
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# edit .env if your Postgres/Redis aren't on default ports
```

### 4. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

The schema auto-migrates on startup — no manual migration step needed.

### 5. Seed test ads

```bash
python -m scripts.seed_ads
```

### 6. Test it

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What running shoes do you recommend?", "session_id": "test-123"}'
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Main chat endpoint (orchestrator) |
| GET | `/track/click` | Click tracking redirect |
| POST | `/admin/ads` | Bulk create ads |
| GET | `/admin/ads` | List ads |
| PATCH | `/admin/ads/{ad_id}` | Update an ad |
| DELETE | `/admin/ads/{ad_id}` | Soft-delete an ad |
| GET | `/analytics/summary` | Dashboard metrics |
| GET | `/health` | Health check |

Full OpenAPI docs at `http://localhost:8000/docs` once the server is running.

---

## Connecting Your React Frontend

The backend is designed to drop in behind your existing React chat UI. Here's how to wire them up.

### CORS

The backend already allows `http://localhost:3000` and `http://localhost:5173` (Vite's default). If your React dev server runs on a different port, add it to `CORS_ORIGINS` in `.env`.

### Chat Integration

Replace your current chat submission handler with a call to `POST /chat`:

```tsx
// src/api/chat.ts

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ChatResponse {
  response: string;
  ad_metadata: {
    ad_id: string;
    sponsored: boolean;
  } | null;
}

export async function sendMessage(
  message: string,
  sessionId: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`);
  }

  return res.json();
}
```

### Session ID

Generate a session ID when the chat starts and reuse it for the entire conversation. A UUID works fine:

```tsx
// generate once per chat session
const sessionId = crypto.randomUUID();
```

### Rendering Sponsored Content

The LLM response contains markdown. Specifically:
- `[Sponsored]` markers before product mentions
- Markdown links like `[Nike Pegasus 41](http://localhost:8000/track/click?...)`

You'll want to parse these in your message renderer:

```tsx
// src/components/ChatMessage.tsx
import ReactMarkdown from "react-markdown";

function ChatMessage({ text }: { text: string }) {
  // replace [Sponsored] with a styled badge
  const withBadge = text.replace(
    /\[Sponsored\]/g,
    '<span class="sponsored-badge">Sponsored</span>'
  );

  return (
    <div className="message assistant">
      <ReactMarkdown
        components={{
          // make sure links open in a new tab (they go through /track/click)
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {withBadge}
      </ReactMarkdown>
    </div>
  );
}
```

And some CSS for the badge:

```css
.sponsored-badge {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  color: #666;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  margin-right: 4px;
  vertical-align: middle;
}
```

### Click Tracking

Tracking links already point to `/track/click` on the backend — the redirect happens server-side. As long as your React app renders the markdown links as real `<a>` tags, clicks are tracked automatically. No extra frontend work needed.

### Full Example: Chat Component

```tsx
import { useState, useRef } from "react";
import { sendMessage } from "../api/chat";
import ChatMessage from "./ChatMessage";

const sessionId = crypto.randomUUID();

export default function Chat() {
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; text: string }[]
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);

    try {
      const data = await sendMessage(userMsg, sessionId);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.response },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((m, i) => (
          <ChatMessage key={i} text={m.text} role={m.role} />
        ))}
        {loading && <div className="typing-indicator">Thinking...</div>}
      </div>
      <div className="input-bar">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type a message..."
        />
        <button onClick={handleSend} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}
```

### Environment Variable

Add to your React app's `.env`:

```
VITE_API_URL=http://localhost:8000
```

---

## Switching from Mock to Real AI Modules

When your AI teammate delivers their modules:

1. Drop their code into `app/services/ai_real.py`
2. Change `AI_MODULE_MODE=real` in `.env`
3. Restart the server

That's it — the dispatcher in `app/services/ai.py` handles the rest.

---

## Project Structure

```
ad-llm-backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan, schema migration
│   ├── core/
│   │   ├── config.py         # Pydantic settings from .env
│   │   ├── db.py             # Postgres + Redis connection pools
│   │   ├── exceptions.py     # Custom error types
│   │   └── logging.py        # Structured logging setup
│   ├── models/
│   │   └── schemas.py        # All data types + API schemas
│   ├── routers/
│   │   ├── chat.py           # POST /chat (main orchestrator)
│   │   ├── track.py          # GET /track/click
│   │   ├── admin.py          # Ad CRUD endpoints
│   │   ├── analytics.py      # GET /analytics/summary
│   │   └── health.py         # GET /health
│   └── services/
│       ├── ai.py             # Dispatcher (mock vs real)
│       ├── ai_mock.py        # Mock AI modules
│       ├── ai_real.py        # Real AI modules (teammate fills in)
│       ├── ads.py            # Ad retrieval + re-ranking (Contract 4)
│       ├── session.py        # Redis session management
│       └── tracking.py       # Tracking URLs + event logging
├── scripts/
│   └── seed_ads.py           # Populate test ad data
├── docker-compose.yml        # Postgres + Redis for local dev
├── requirements.txt
├── .env.example
└── README.md
```
