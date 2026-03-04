import { useState, useCallback } from 'react'
import { useChat } from './hooks/useChat'
import Sidebar from './components/SideBar/Sidebar'
import ChatWindow from './components/ChatWindow/ChatWindow'
import './app.css'   

export default function App() {
  const chat = useChat()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [renamingId, setRenamingId] = useState(null)

  const handleNewChat = useCallback(() => {
    chat.newConversation()
  }, [chat])

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(prev => !prev)
  }, [])

  return (
    <div className={`app ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        conversations={chat.conversations}
        activeId={chat.activeId}
        renamingId={renamingId}
        isStreaming={chat.isStreaming}
        onNewChat={handleNewChat}
        onSelect={chat.selectConversation}
        onDelete={chat.deleteConversation}
        onRename={chat.renameConversation}
        onStartRename={setRenamingId}
        onStopRename={() => setRenamingId(null)}
        onToggle={toggleSidebar}
      />

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={toggleSidebar} />
      )}

      {/* Main chat area */}
      <main className="main">
        <ChatWindow
          conversation={chat.activeConversation}
          messages={chat.messages}
          streamingId={chat.streamingId}
          isThinking={chat.isThinking}
          isStreaming={chat.isStreaming}
          sidebarOpen={sidebarOpen}
          onSendMessage={chat.sendMessage}
          onStopStreaming={chat.stopStreaming}
          onRegenerateResponse={chat.regenerateLastResponse}
          onToggleSidebar={toggleSidebar}
          onNewChat={handleNewChat}
        />
      </main>
    </div>
  )
}