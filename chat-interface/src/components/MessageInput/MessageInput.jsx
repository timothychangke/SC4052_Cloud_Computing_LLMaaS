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

const IconImage = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
    <rect x="1.5" y="2.5" width="13" height="11" rx="2" stroke="currentColor" strokeWidth="1.5"/>
    <circle cx="5.5" cy="6" r="1.25" stroke="currentColor" strokeWidth="1.25"/>
    <path d="M1.5 11l3.5-3.5 2.5 2.5 2-2 3 3.5" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const IconChat = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
    <path d="M14 2H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3l2 2 2-2h5a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
  </svg>
)

const MAX_ROWS = 10

export default function MessageInput({ isStreaming, onSend, onSendImage, onStop }) {
  const [value, setValue] = useState('')
  const [imageMode, setImageMode] = useState(false)
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const lineHeight = 24
    const maxHeight = lineHeight * MAX_ROWS + 32
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
    if (imageMode) {
      onSendImage?.(trimmed)
    } else {
      onSend(trimmed)
    }
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value, isStreaming, imageMode, onSend, onSendImage])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const toggleMode = useCallback(() => {
    setImageMode(prev => !prev)
    setValue('')
    textareaRef.current?.focus()
  }, [])

  const canSend = value.trim().length > 0 && !isStreaming

  const placeholder = isStreaming
    ? 'Waiting for response…'
    : imageMode
      ? 'Describe the image you want to generate…'
      : 'Ask Anything…'

  return (
    <div className="input-area">
      {/* ── Mode toggle pill ── */}
      <div className="mode-toggle-row">
        <div className="mode-toggle-pill">
          <button
            className={`mode-pill-btn ${!imageMode ? 'active' : ''}`}
            onClick={() => { if (imageMode) toggleMode() }}
            disabled={isStreaming}
            title="Text chat"
          >
            <IconChat />
            <span>Chat</span>
          </button>
          <button
            className={`mode-pill-btn ${imageMode ? 'active' : ''}`}
            onClick={() => { if (!imageMode) toggleMode() }}
            disabled={isStreaming}
            title="Image generation"
          >
            <IconImage />
            <span>Image</span>
          </button>
        </div>
      </div>

      {/* ── Input container ── */}
      <div className={`input-container ${imageMode ? 'image-mode' : ''}`}>
        <textarea
          ref={textareaRef}
          className="message-textarea"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isStreaming}
          rows={1}
          aria-label="Message input"
        />

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
              className={`send-btn ${canSend ? 'active' : ''} ${imageMode && canSend ? 'image-send' : ''}`}
              onClick={handleSend}
              disabled={!canSend}
              title={imageMode ? 'Generate image' : 'Send message'}
              aria-label={imageMode ? 'Generate image' : 'Send message'}
            >
              {imageMode ? <IconImage /> : <IconSend />}
            </button>
          )}
        </div>
      </div>

      {imageMode && (
        <p className="image-mode-label">
          Image generation — product placement may be added automatically
        </p>
      )}

      <p className="input-disclaimer">
        ChatGPT can make mistakes. Verify important information.
      </p>
    </div>
  )
}
