import { useEffect, useRef } from 'react'
import Message from '../Message/Message'
import MessageInput from '../MessageInput/MessageInput'
import './ChatWindow.css'
import logo from "../../assets/logo.png"

// ─── Icons ──────────────────────────────────────────────────────
const IconMenu = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
    <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
  </svg>
)

const IconRefresh = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
    <path d="M13.5 8A5.5 5.5 0 1 1 11 3.07" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    <path d="M11 1v2.5L13.5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

// ─── Starter prompts for the welcome screen ──────────────────────
const STARTER_PROMPTS = [
  { icon: '⚡', label: 'Explain React hooks', prompt: 'Can you explain how React hooks work with examples?' },
  { icon: '🎨', label: 'CSS architecture tips', prompt: 'What are best practices for CSS architecture in large projects?' },
  { icon: '🛠️', label: 'Build a REST API', prompt: 'Show me how to build a simple REST API with Node.js and Express' },
  { icon: '📊', label: 'Sorting algorithms', prompt: 'Explain common sorting algorithms and their time complexities' },
]

// ─── Welcome / empty state ───────────────────────────────────────
function WelcomeScreen({ onPromptClick }) {
  return (
    <div className="welcome">
      <div className="welcome-inner">
        <div className="welcome-logo">
          <img src={logo} alt="logo" className="welcome-logo-img" />
       </div>
        <h1 className="welcome-title">Pro Intelligence. Zero Subscriptions.</h1>
        <p className="welcome-sub">Access the world's most powerful models for free—powered by brands you’ll actually like.</p>

        <div className="starter-grid">
          {STARTER_PROMPTS.map(({ icon, label, prompt }) => (
            <button
              key={label}
              className="starter-card"
              onClick={() => onPromptClick(prompt)}
            >
              <span className="starter-icon">{icon}</span>
              <span className="starter-label">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Chat window ─────────────────────────────────────────────────
export default function ChatWindow({
  conversation,
  messages,
  streamingId,
  isThinking,
  isStreaming,
  sidebarOpen,
  onSendMessage,
  onSendImage,
  onStopStreaming,
  onRegenerateResponse,
  onToggleSidebar,
  onNewChat,
}) {
  const bottomRef = useRef(null)
  const scrollRef = useRef(null)
  const userScrolledUp = useRef(false)

  // Auto-scroll to bottom while streaming, unless user scrolled up
  useEffect(() => {
    if (!isStreaming) {
      userScrolledUp.current = false
    }
    if (!userScrolledUp.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isStreaming])

  // Detect manual upward scroll
  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    userScrolledUp.current = distFromBottom > 80
  }

  const isEmpty = messages.length === 0

  // Whether to show the regenerate button below the last message
  const lastMsg = messages[messages.length - 1]
  const canRegenerate = !isStreaming && lastMsg?.role === 'assistant' && messages.length >= 2

  return (
    <div className="chat-window">
      {/* Header bar */}
      <header className="chat-header">
        <div className="chat-header-left">
          {!sidebarOpen && (
            <button className="icon-btn" onClick={onToggleSidebar} title="Open sidebar">
              <IconMenu />
            </button>
          )}
          <span className="chat-header-title">
            {conversation?.title ?? 'ChatGPT'}
          </span>
        </div>
        <div className="chat-header-right">
          <button className="header-new-btn" onClick={onNewChat}>
            + New chat
          </button>
        </div>
      </header>

      {/* Messages / welcome */}
      <div className="chat-scroll" ref={scrollRef} onScroll={handleScroll}>
        {isEmpty ? (
          <WelcomeScreen onPromptClick={onSendMessage} />
        ) : (
          <div className="messages-list">
            {messages.map((msg, i) => (
              <Message
                key={msg.id}
                message={msg}
                isStreaming={streamingId === msg.id}
                isThinking={isThinking && streamingId === msg.id}
                isLast={i === messages.length - 1}
              />
            ))}

            {/* Regenerate button */}
            {canRegenerate && (
              <div className="regen-row">
                <button className="regen-btn" onClick={onRegenerateResponse}>
                  <IconRefresh />
                  Regenerate response
                </button>
              </div>
            )}

            <div ref={bottomRef} style={{ height: 1 }} />
          </div>
        )}
      </div>

      {/* Input */}
      <MessageInput
        isStreaming={isStreaming}
        onSend={onSendMessage}
        onSendImage={onSendImage}
        onStop={onStopStreaming}
      />
    </div>
  )
}