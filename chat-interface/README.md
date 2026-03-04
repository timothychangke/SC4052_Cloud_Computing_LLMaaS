A full-featured ChatGPT-style chat interface built with React + Vite.

## Features

- **Conversation management** — create, rename, delete, switch between chats
- **Simulated AI streaming** — token-by-token response animation with stop support
- **Markdown rendering** — full GFM markdown: headings, lists, tables, blockquotes
- **Syntax-highlighted code blocks** — with language labels and one-click copy
- **Regenerate response** — resend the last message and get a fresh answer
- **Responsive** — collapsible sidebar, works on mobile
- **Accessible** — keyboard navigation, focus management, ARIA labels

## Tech Stack

| Layer         | Library                          |
|--------------|----------------------------------|
| Framework     | React 18                         |
| Build tool    | Vite 5                           |
| Markdown      | react-markdown + remark-gfm      |
| Code highlight| react-syntax-highlighter (Prism) |
| IDs           | uuid                             |

## Quick Start

```bash
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

## Project Structure

```
src/
├── main.jsx                  # React entry point
├── App.jsx                   # Root layout (sidebar + main)
├── App.css
├── index.css                 # Global styles + CSS tokens
│
├── hooks/
│   └── useChat.js            # All chat state & streaming logic
│
├── utils/
│   └── mockResponses.js      # Simulated AI responses + streamer
│
└── components/
    ├── Sidebar.jsx            # Conversation list, new chat, rename/delete
    ├── Sidebar.css
    ├── ChatWindow.jsx         # Welcome screen, message list, header
    ├── ChatWindow.css
    ├── Message.jsx            # Individual message (user + AI + markdown)
    ├── Message.css
    ├── MessageInput.jsx       # Auto-grow textarea, send/stop button
    └── MessageInput.css
```

## Connecting a Real AI Backend

Replace the `streamResponse` function in `src/utils/mockResponses.js` with a real
streaming API call. For example, with the OpenAI API:

```js
export async function streamResponse(prompt, onChunk, isCancelled) {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${import.meta.env.VITE_OPENAI_KEY}\`,
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      stream: true,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done || isCancelled()) break;

    const lines = decoder.decode(value).split('\\n');
    for (const line of lines) {
      if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;
      const delta = JSON.parse(line.slice(6)).choices[0]?.delta?.content;
      if (delta) onChunk(delta);
    }
  }
}
```

Add your key to `.env.local`:
```
VITE_OPENAI_KEY=sk-...
```

## Customisation

All colours, spacing, and typography are defined as CSS custom properties in
`src/index.css` under `:root { ... }`. Change `--accent` to retheme the entire
app in one line.