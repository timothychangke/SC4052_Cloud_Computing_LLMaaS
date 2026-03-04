import { useState, useRef, useEffect } from 'react'
import './Sidebar.css'
import logo from '../../assets/logo.png'   

// ─── Icons ──────────────────────────────────────────────────────
const IconPlus = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
  </svg>
)

const IconChat = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <path d="M14 2H2a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3l3 3 3-3h3a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1Z"
      stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
  </svg>
)

const IconEdit = () => (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
    <path d="M11 2l3 3-9 9H2v-3l9-9Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
  </svg>
)

const IconTrash = () => (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
    <path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 10h8L13 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const IconCheck = () => (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
    <path d="M2 8l4.5 4.5L14 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const IconX = () => (
  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
    <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
  </svg>
)

const IconChevronLeft = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

// ─── Group conversations by time ────────────────────────────────
function groupByTime(conversations) {
  const now = Date.now()
  const oneDay = 86400_000
  const oneWeek = 7 * oneDay
  const oneMonth = 30 * oneDay

  const groups = { Today: [], 'Yesterday': [], 'Last 7 Days': [], 'Last 30 Days': [], Older: [] }

  for (const conv of conversations) {
    const age = now - conv.createdAt
    if (age < oneDay)       groups['Today'].push(conv)
    else if (age < 2*oneDay) groups['Yesterday'].push(conv)
    else if (age < oneWeek) groups['Last 7 Days'].push(conv)
    else if (age < oneMonth) groups['Last 30 Days'].push(conv)
    else                    groups['Older'].push(conv)
  }

  return Object.entries(groups).filter(([, items]) => items.length > 0)
}

// ─── Single conversation row ─────────────────────────────────────
function ConvItem({ conv, isActive, isRenaming, isStreaming, onSelect, onDelete, onStartRename, onConfirmRename, onCancelRename }) {
  const [hovered, setHovered] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [editValue, setEditValue] = useState(conv.title)
  const inputRef = useRef(null)

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isRenaming])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') onConfirmRename(conv.id, editValue)
    if (e.key === 'Escape') onCancelRename()
  }

  return (
    <div
      className={`conv-item ${isActive ? 'active' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setMenuOpen(false) }}
      onClick={() => !isRenaming && onSelect(conv.id)}
    >
      <span className="conv-icon"><IconChat /></span>

      {isRenaming ? (
        <input
          ref={inputRef}
          className="conv-rename-input"
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => onConfirmRename(conv.id, editValue)}
          onClick={e => e.stopPropagation()}
        />
      ) : (
        <span className="conv-title">{conv.title}</span>
      )}

      {isRenaming ? (
        <div className="conv-actions">
          <button
            className="conv-action-btn"
            onClick={e => { e.stopPropagation(); onConfirmRename(conv.id, editValue) }}
            title="Confirm"
          >
            <IconCheck />
          </button>
          <button
            className="conv-action-btn"
            onClick={e => { e.stopPropagation(); onCancelRename() }}
            title="Cancel"
          >
            <IconX />
          </button>
        </div>
      ) : (hovered || menuOpen) && !isStreaming ? (
        <div className="conv-actions" onClick={e => e.stopPropagation()}>
          <button
            className="conv-action-btn"
            onClick={() => { onStartRename(conv.id); setEditValue(conv.title) }}
            title="Rename"
          >
            <IconEdit />
          </button>
          <button
            className="conv-action-btn danger"
            onClick={() => onDelete(conv.id)}
            title="Delete"
          >
            <IconTrash />
          </button>
        </div>
      ) : null}
    </div>
  )
}

// ─── Sidebar component ───────────────────────────────────────────
export default function Sidebar({
  open,
  conversations,
  activeId,
  renamingId,
  isStreaming,
  onNewChat,
  onSelect,
  onDelete,
  onRename,
  onStartRename,
  onStopRename,
  onToggle,
}) {
  const grouped = groupByTime(conversations)

  return (
    <aside className={`sidebar ${open ? 'open' : 'closed'}`}>
      {/* Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <img src={logo} alt="logo" className="sidebar-logo-img" />
          <span>ChatGPT</span>
        </div>
        <button className="icon-btn toggle-btn" onClick={onToggle} title="Close sidebar">
          <IconChevronLeft />
        </button>
      </div>

      {/* New Chat */}
      <div className="sidebar-top">
        <button className="new-chat-btn" onClick={onNewChat}>
          <IconPlus />
          <span>New chat</span>
        </button>
      </div>

      {/* Conversation list */}
      <div className="sidebar-scroll">
        {conversations.length === 0 ? (
          <div className="sidebar-empty">
            <p>No conversations yet.</p>
            <p>Start a new chat!</p>
          </div>
        ) : (
          grouped.map(([label, convs]) => (
            <div key={label} className="conv-group">
              <div className="conv-group-label">{label}</div>
              {convs.map(conv => (
                <ConvItem
                  key={conv.id}
                  conv={conv}
                  isActive={conv.id === activeId}
                  isRenaming={renamingId === conv.id}
                  isStreaming={isStreaming}
                  onSelect={onSelect}
                  onDelete={onDelete}
                  onStartRename={onStartRename}
                  onConfirmRename={(id, title) => {
                    onRename(id, title || conv.title)
                    onStopRename()
                  }}
                  onCancelRename={onStopRename}
                />
              ))}
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="user-avatar">U</div>
          <div className="user-info">
            <span className="user-name">User</span>
            <span className="user-plan">Free plan</span>
          </div>
        </div>
      </div>
    </aside>
  )
}