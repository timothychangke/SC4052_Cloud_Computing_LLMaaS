import { useState, useRef, useEffect, useCallback } from 'react'
import './MessageInput.css'

// ─── Icons ───────────────────────────────────────────────────────
const IconSend = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M14 8L2 2l3 6-3 6 12-6Z" fill="currentColor"/>
  </svg>
)

const IconStop = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <rect x="3" y="3" width="10" height="10" rx="2" fill="currentColor"/>
  </svg>
)

const MAX_ROWS = 10

export default function MessageInput({ isStreaming, onSend, onStop }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const lineHeight = 24
    const maxHeight = lineHeight * MAX_ROWS + 32 // padding
    el.style.height = Math.min(el.scrollHeight, maxHeight) + 'px'
  }, [value])

  // Re-focus after streaming stops
  useEffect(() => {
    if (!isStreaming) {
      textareaRef.current?.focus()
    }
  }, [isStreaming])

  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || isStreaming) return
    onSend(trimmed)
    setValue('')
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value, isStreaming, onSend])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const canSend = value.trim().length > 0 && !isStreaming

  return (
    <div className="input-area">
      <div className="input-container">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          className="message-textarea"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'Waiting for response…' : 'Ask Anything…'}
          disabled={isStreaming}
          rows={1}
          aria-label="Message input"
        />

        {/* Send / Stop button */}
        <div className="input-actions">
          {isStreaming ? (
            <button
              className="send-btn stop"
              onClick={onStop}
              title="Stop generating"
              aria-label="Stop generating"
            >
              <IconStop />
            </button>
          ) : (
            <button
              className={`send-btn ${canSend ? 'active' : ''}`}
              onClick={handleSend}
              disabled={!canSend}
              title="Send message"
              aria-label="Send message"
            >
              <IconSend />
            </button>
          )}
        </div>
      </div>

      <p className="input-disclaimer">
        ChatGPT can make mistakes. Verify important information.
      </p>
    </div>
  )
}