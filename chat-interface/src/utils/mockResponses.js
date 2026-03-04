/**
 * Mock AI responses for demonstration.
 * In production, replace streamResponse() with a real API call
 * (e.g. OpenAI, Anthropic, etc.) using their streaming SSE endpoints.
 */

const RESPONSES = [
  `Sure! Here's a quick overview of how **React hooks** work:

## Core Hooks

### useState
Manages local component state:
\`\`\`jsx
const [count, setCount] = useState(0);
\`\`\`

### useEffect
Runs side effects after render:
\`\`\`jsx
useEffect(() => {
  document.title = \`Count: \${count}\`;
}, [count]); // dependency array
\`\`\`

### useCallback / useMemo
Memoize functions and values to avoid unnecessary re-renders:
\`\`\`jsx
const doubled = useMemo(() => value * 2, [value]);
const handler = useCallback(() => doSomething(id), [id]);
\`\`\`

## Rules of Hooks
1. Only call hooks **at the top level** — never inside loops or conditions.
2. Only call hooks from **React functions** (components or custom hooks).

Want me to dive deeper into any specific hook?`,

  `Great question! Here are some **best practices for CSS architecture** in large projects:

## 1. Use a Naming Convention
**BEM** (Block Element Modifier) is popular:
\`\`\`css
.card { }
.card__title { }
.card__title--highlighted { }
\`\`\`

## 2. CSS Custom Properties
Define tokens at the root for consistency:
\`\`\`css
:root {
  --color-primary: #f59e0b;
  --spacing-md: 1rem;
  --radius: 8px;
}
\`\`\`

## 3. Co-locate Styles
Keep component styles next to their component files. Avoid massive global stylesheets.

## 4. Utility Classes for Micro-styles
Use utility helpers for one-off needs rather than creating new class names.

## 5. Avoid Deep Nesting
Keep specificity low. Deeply nested selectors are fragile and hard to override.

Let me know if you'd like a full example project structure!`,

  `Here's a simple **REST API in Node.js** using Express:

\`\`\`js
import express from 'express';
const app = express();
app.use(express.json());

// In-memory data store
let items = [
  { id: 1, name: 'Widget A' },
  { id: 2, name: 'Widget B' },
];

// GET all items
app.get('/items', (req, res) => {
  res.json(items);
});

// GET single item
app.get('/items/:id', (req, res) => {
  const item = items.find(i => i.id === Number(req.params.id));
  if (!item) return res.status(404).json({ error: 'Not found' });
  res.json(item);
});

// POST create item
app.post('/items', (req, res) => {
  const newItem = { id: Date.now(), ...req.body };
  items.push(newItem);
  res.status(201).json(newItem);
});

// DELETE item
app.delete('/items/:id', (req, res) => {
  items = items.filter(i => i.id !== Number(req.params.id));
  res.status(204).send();
});

app.listen(3000, () => console.log('Server running on http://localhost:3000'));
\`\`\`

**To run it:**
\`\`\`bash
npm init -y
npm install express
node server.js
\`\`\`

This covers all the basic CRUD operations. Want me to add authentication or database integration?`,

  `That's a nuanced topic. Let me break it down:

## TypeScript vs JavaScript

**TypeScript advantages:**
- Catches type errors at compile-time, not runtime
- Better IDE autocomplete and refactoring support
- Self-documenting code — types act as inline documentation
- Scales better for large teams and codebases

**JavaScript advantages:**
- Zero setup — just run it
- Less boilerplate for small scripts
- Easier to prototype quickly
- No build step required

## My Take

For anything beyond a quick script or prototype, **TypeScript is almost always worth it**. The upfront cost of adding types pays dividends in reduced bugs, better tooling, and easier onboarding for new developers.

> The bigger the team, the more valuable TypeScript becomes.

## Getting Started
\`\`\`bash
npm create vite@latest my-app -- --template react-ts
\`\`\`

Would you like a guide on migrating an existing JS project to TypeScript?`,

  `Of course! Here's a concise explanation of **how the internet works**:

## The Journey of a Web Request

1. **You type a URL** like \`https://example.com\` into your browser.

2. **DNS Lookup** — Your computer asks a DNS server *"What IP address is example.com?"* and gets back something like \`93.184.216.34\`.

3. **TCP Handshake** — Your browser opens a connection to that IP address on port 443 (HTTPS).

4. **TLS Handshake** — Your browser and the server exchange encryption keys so the connection is secure.

5. **HTTP Request** — Your browser sends:
\`\`\`
GET / HTTP/1.1
Host: example.com
Accept: text/html
\`\`\`

6. **Server Response** — The server sends back HTML, CSS, JavaScript files.

7. **Rendering** — Your browser parses the HTML, fetches additional assets, runs JavaScript, and paints the page on screen.

The whole round-trip typically takes **50–300ms** depending on network conditions and server location.

Want me to go deeper on any step — like how TLS encryption works, or how browsers render HTML?`,

  `Here's a breakdown of **common sorting algorithms** with their complexities:

| Algorithm      | Best     | Average  | Worst    | Space   |
|---------------|----------|----------|----------|---------|
| Bubble Sort   | O(n)     | O(n²)    | O(n²)    | O(1)    |
| Merge Sort    | O(n log n)| O(n log n)| O(n log n)| O(n)  |
| Quick Sort    | O(n log n)| O(n log n)| O(n²)   | O(log n)|
| Heap Sort     | O(n log n)| O(n log n)| O(n log n)| O(1)  |
| Insertion Sort| O(n)     | O(n²)    | O(n²)    | O(1)    |

## Quick Sort implementation (JavaScript):
\`\`\`js
function quickSort(arr) {
  if (arr.length <= 1) return arr;

  const pivot = arr[Math.floor(arr.length / 2)];
  const left  = arr.filter(x => x < pivot);
  const mid   = arr.filter(x => x === pivot);
  const right = arr.filter(x => x > pivot);

  return [...quickSort(left), ...mid, ...quickSort(right)];
}

console.log(quickSort([3, 6, 8, 10, 1, 2, 1]));
// → [1, 1, 2, 3, 6, 8, 10]
\`\`\`

In practice, most languages use a **hybrid** of Quick Sort and Insertion Sort (called Timsort) for their built-in sort functions.`,
];

const THINKING_PHRASES = [
  "Thinking…",
  "Let me think about that…",
  "On it…",
  "Sure, let me put that together…",
];

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function streamResponse(prompt, sessionId, onChunk, isCancelled) {
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: prompt,
        session_id: sessionId, // Use the real session ID
      }),
    });

    if (!response.ok) throw new Error(`Backend error: ${response.status}`);

    const data = await response.json();
    
    // Since your backend currently returns a full JSON object (not a stream),
    // we simulate the "streaming" effect for your UI's animation.
    const fullText = data.response;
    const words = fullText.split(" ");
    
    for (const word of words) {
      if (isCancelled()) break;
      onChunk(word + " ");
      // Artificial delay to keep your UI's "token" animation smooth
      await new Promise((resolve) => setTimeout(resolve, 30)); 
    }
  } catch (error) {
    onChunk("Error: Could not connect to the ad orchestrator.");
    console.error(error);
  }
}

// /**
//  * Simulate streaming an AI response token-by-token.
//  * @param {string} prompt - The user's message (used to pick a response)
//  * @param {(chunk: string) => void} onChunk - Called with each new chunk of text
//  * @param {() => boolean} isCancelled - Return true to abort streaming
//  * @returns {Promise<void>}
//  */
// export async function streamResponse(prompt, onChunk, isCancelled) {
//   // Pick a pseudo-random response
//   const index = Math.floor(Math.random() * RESPONSES.length);
//   const fullText = RESPONSES[index];

//   // Simulate variable "thinking" delay
//   await sleep(600 + Math.random() * 400);

//   if (isCancelled()) return;

//   // Stream word-by-word with realistic timing
//   const words = fullText.split(/(\s+)/);
//   let buffer = '';

//   for (const token of words) {
//     if (isCancelled()) return;

//     buffer += token;

//     // Flush the buffer in small chunks
//     if (buffer.length >= 4 || token.includes('\n')) {
//       onChunk(buffer);
//       buffer = '';

//       // Variable delay: faster for normal text, brief pause at punctuation
//       const delay = token.match(/[.!?\n]/) ? 60 + Math.random() * 40 : 18 + Math.random() * 22;
//       await sleep(delay);
//     }
//   }

//   // Flush remaining buffer
//   if (buffer && !isCancelled()) {
//     onChunk(buffer);
//   }
// }

/**
 * Get a random "thinking" label shown while the AI is preparing
 */
export function getThinkingPhrase() {
  return THINKING_PHRASES[Math.floor(Math.random() * THINKING_PHRASES.length)];
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}