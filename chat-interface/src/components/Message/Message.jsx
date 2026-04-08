import { useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './Message.css'

// ─── Icons ──────────────────────────────────────────────────────
const IconCopy = () => (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
    <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M3 11H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v1" stroke="currentColor" strokeWidth="1.5"/>
  </svg>
)

const IconCheck = () => (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
    <path d="M2 8l4.5 4.5L14 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const IconThumbUp = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <path d="M5 14V7.5L9 2l1 .5.5 3H14l-1 8H5ZM5 7.5H2v6.5h3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
  </svg>
)

const IconThumbDown = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <path d="M11 2v6.5L7 14l-1-.5-.5-3H2l1-8h8ZM11 8.5H14V2h-3" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
  </svg>
)

// ─── Copy button with "copied" feedback ─────────────────────────
function CopyButton({ text, className = '' }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard not available — silently ignore
    }
  }, [text])

  return (
    <button
      className={`copy-btn ${copied ? 'copied' : ''} ${className}`}
      onClick={handleCopy}
      title={copied ? 'Copied!' : 'Copy'}
    >
      {copied ? <IconCheck /> : <IconCopy />}
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  )
}

// ─── Code block with language label + copy ──────────────────────
function CodeBlock({ language, code }) {
  return (
    <div className="code-block">
      <div className="code-header">
        <span className="code-lang">{language || 'code'}</span>
        <CopyButton text={code} />
      </div>
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: '0 0 8px 8px',
          padding: '16px',
          fontSize: '13px',
          lineHeight: '1.6',
          background: '#0d0d10',
          fontFamily: 'IBM Plex Mono, monospace',
        }}
        codeTagProps={{ style: { fontFamily: 'IBM Plex Mono, monospace' } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

// ─── Markdown renderer config ────────────────────────────────────
const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '')
    const code = String(children).replace(/\n$/, '')

    if (!inline) {
      return <CodeBlock language={match?.[1]} code={code} />
    }

    return (
      <code className="inline-code" {...props}>
        {children}
      </code>
    )
  },
  table({ children }) {
    return (
      <div className="table-wrapper">
        <table>{children}</table>
      </div>
    )
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    )
  },
  text({ children }) {
    if (typeof children === 'string' && children.includes('[Sponsored]')) {
      const parts = children.split(/(\[Sponsored\])/g);
      return (
        <>
          {parts.map((part, i) => 
            part === '[Sponsored]' 
              ? <span key={i} className="sponsored-badge">Sponsored</span> 
              : part
          )}
        </>
      );
    }
    return children;
  }
}

// ─── Thinking / loading indicator ────────────────────────────────
function ThinkingIndicator() {
  return (
    <div className="thinking-indicator">
      <span className="thinking-dot" style={{ animationDelay: '0ms' }} />
      <span className="thinking-dot" style={{ animationDelay: '160ms' }} />
      <span className="thinking-dot" style={{ animationDelay: '320ms' }} />
    </div>
  )
}

// ─── Cursor that blinks at end of streaming text ─────────────────
function StreamCursor() {
  return <span className="stream-cursor" aria-hidden="true" />
}

// ─── Generated image bubble ──────────────────────────────────────
function ImageBubble({ imageUrl, enhancedPrompt, adMetadata }) {
  const [loaded, setLoaded] = useState(false)
  const [errored, setErrored] = useState(false)

  return (
    <div className="generated-image-wrap">
      {!loaded && !errored && <div className="image-skeleton" />}
      {errored ? (
        <div className="image-error">Image could not be loaded.</div>
      ) : (
        <img
          className={`generated-image ${loaded ? 'loaded' : ''}`}
          src={imageUrl}
          alt={enhancedPrompt || 'Generated image'}
          onLoad={() => setLoaded(true)}
          onError={() => setErrored(true)}
        />
      )}
      {loaded && enhancedPrompt && (
        <p className="image-prompt-caption">
          {adMetadata && <span className="sponsored-badge">Sponsored</span>}
          {enhancedPrompt}
        </p>
      )}
    </div>
  )
}

// ─── Message component ───────────────────────────────────────────
export default function Message({ message, isStreaming, isThinking }) {
  const [feedback, setFeedback] = useState(null) // 'up' | 'down' | null
  const isUser = message.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content-wrap">
        {/* Avatar */}
        <div className="message-avatar">
          {isUser ? (
            <div className="avatar user-avatar-icon">U</div>
          ) : (
            <div className="avatar assistant-avatar-icon">✦</div>
          )}
        </div>

        {/* Bubble / content */}
        <div className="message-body">
          {isUser ? (
            <div className="user-bubble">
              {message.isImagePrompt && (
                <span className="image-prompt-icon" title="Image generation prompt">🖼</span>
              )}
              <span>{message.content}</span>
            </div>
          ) : (
            <div className="assistant-body">
              {isThinking ? (
                <ThinkingIndicator />
              ) : message.imageUrl ? (
                /* ── Generated image response ── */
                <ImageBubble
                  imageUrl={message.imageUrl}
                  enhancedPrompt={message.enhancedPrompt}
                  adMetadata={message.adMetadata}
                />
              ) : (
                <>
                  <div className="assistant-markdown">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {message.content}
                    </ReactMarkdown>
                    {isStreaming && <StreamCursor />}
                  </div>

                  {/* Actions row (only when not streaming) */}
                  {!isStreaming && message.content && (
                    <div className="message-actions">
                      <CopyButton text={message.content} className="action-copy" />
                      <button
                        className={`action-btn ${feedback === 'up' ? 'active' : ''}`}
                        onClick={() => setFeedback(prev => prev === 'up' ? null : 'up')}
                        title="Good response"
                      >
                        <IconThumbUp />
                      </button>
                      <button
                        className={`action-btn ${feedback === 'down' ? 'active' : ''}`}
                        onClick={() => setFeedback(prev => prev === 'down' ? null : 'down')}
                        title="Bad response"
                      >
                        <IconThumbDown />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}