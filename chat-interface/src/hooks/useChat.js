import { useState, useRef, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { streamResponse, generateImage, getThinkingPhrase } from '../utils/mockResponses'

/**
 * useChat — manages all chat state:
 * - Multiple conversations (sidebar history)
 * - Per-conversation message lists
 * - Streaming AI responses
 * - Stop-generation support
 */
export function useChat() {
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [streamingId, setStreamingId] = useState(null)   // message id currently streaming
  const [isThinking, setIsThinking] = useState(false)    // "thinking" phase before first token
  const cancelRef = useRef(false)

  // ── Derived: current conversation's messages ────────────────────
  const activeConversation = conversations.find(c => c.id === activeId) ?? null
  const messages = activeConversation?.messages ?? []

  // ── Create a new empty conversation ────────────────────────────
  const newConversation = useCallback(() => {
    const id = uuidv4()
    setConversations(prev => [
      { id, title: 'New Chat', createdAt: Date.now(), messages: [] },
      ...prev,
    ])
    setActiveId(id)
  }, [])

  // ── Switch to an existing conversation ──────────────────────────
  const selectConversation = useCallback((id) => {
    if (streamingId) return // don't switch mid-stream
    setActiveId(id)
  }, [streamingId])

  // ── Delete a conversation ───────────────────────────────────────
  const deleteConversation = useCallback((id) => {
    setConversations(prev => prev.filter(c => c.id !== id))
    setActiveId(prev => {
      if (prev !== id) return prev
      const remaining = conversations.filter(c => c.id !== id)
      return remaining[0]?.id ?? null
    })
  }, [conversations])

  // ── Rename a conversation ───────────────────────────────────────
  const renameConversation = useCallback((id, title) => {
    setConversations(prev =>
      prev.map(c => c.id === id ? { ...c, title } : c)
    )
  }, [])

  // ── Internal: update a specific message's content ───────────────
  const updateMessage = useCallback((convId, msgId, patch) => {
    setConversations(prev =>
      prev.map(c => {
        if (c.id !== convId) return c
        return {
          ...c,
          messages: c.messages.map(m =>
            m.id === msgId ? { ...m, ...patch } : m
          ),
        }
      })
    )
  }, [])

  // ── Internal: append a message to a conversation ────────────────
  const appendMessage = useCallback((convId, message) => {
    setConversations(prev =>
      prev.map(c => {
        if (c.id !== convId) return c
        return { ...c, messages: [...c.messages, message] }
      })
    )
  }, [])

  // ── Auto-title a conversation from first user message ───────────
  const autoTitle = useCallback((convId, text) => {
    const title = text.length > 40 ? text.slice(0, 40).trim() + '…' : text.trim()
    setConversations(prev =>
      prev.map(c => c.id === convId && c.title === 'New Chat' ? { ...c, title } : c)
    )
  }, [])

  // ── Stop streaming ───────────────────────────────────────────────
  const stopStreaming = useCallback(() => {
    cancelRef.current = true
  }, [])

  // ── Send a message ───────────────────────────────────────────────
  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return

    // Create a new conversation if none is active
    let convId = activeId
    if (!convId) {
      convId = uuidv4()
      const newConv = { id: convId, title: 'New Chat', createdAt: Date.now(), messages: [] }
      setConversations(prev => [newConv, ...prev])
      setActiveId(convId)
    }

    // Add user message
    const userMsg = { id: uuidv4(), role: 'user', content: text, timestamp: Date.now() }
    appendMessage(convId, userMsg)
    autoTitle(convId, text)

    // Prepare assistant message placeholder
    const assistantMsgId = uuidv4()
    const assistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      thinking: true,
    }
    appendMessage(convId, assistantMsg)

    // Start streaming
    cancelRef.current = false
    setIsThinking(true)
    setStreamingId(assistantMsgId)

    // Brief thinking phase
    await new Promise(r => setTimeout(r, 700))
    if (cancelRef.current) {
      updateMessage(convId, assistantMsgId, { thinking: false, content: '*Response stopped.*' })
      setStreamingId(null)
      setIsThinking(false)
      return
    }

    setIsThinking(false)
    updateMessage(convId, assistantMsgId, { thinking: false })

    let accumulated = ''
    
    await streamResponse(
      text,            
      convId,          
      (chunk) => {     
        accumulated += chunk
        updateMessage(convId, assistantMsgId, { content: accumulated })
      }, 
      () => cancelRef.current
    );

    // Mark as done
    setStreamingId(null)
    cancelRef.current = false
  }, [activeId, appendMessage, autoTitle, updateMessage])

  // ── Send an image-generation request ───────────────────────────────
  const sendImageMessage = useCallback(async (prompt) => {
    if (!prompt.trim()) return

    let convId = activeId
    if (!convId) {
      convId = uuidv4()
      const newConv = { id: convId, title: 'New Chat', createdAt: Date.now(), messages: [] }
      setConversations(prev => [newConv, ...prev])
      setActiveId(convId)
    }

    // User message — flagged so the UI can show the camera icon
    const userMsg = {
      id: uuidv4(),
      role: 'user',
      content: prompt,
      isImagePrompt: true,
      timestamp: Date.now(),
    }
    appendMessage(convId, userMsg)
    autoTitle(convId, prompt)

    // Assistant placeholder while we wait for the image
    const assistantMsgId = uuidv4()
    appendMessage(convId, {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      thinking: true,
    })

    cancelRef.current = false
    setIsThinking(true)
    setStreamingId(assistantMsgId)

    const result = await generateImage(prompt, convId)

    updateMessage(convId, assistantMsgId, {
      thinking: false,
      content: result.image_url ? '' : 'Sorry, image generation failed.',
      imageUrl: result.image_url,
      enhancedPrompt: result.enhanced_prompt,
      adMetadata: result.ad_metadata,
    })

    setStreamingId(null)
    setIsThinking(false)
  }, [activeId, appendMessage, autoTitle, updateMessage])

  // ── Regenerate the last assistant response ───────────────────────
  const regenerateLastResponse = useCallback(async () => {
    if (!activeId || streamingId) return

    const conv = conversations.find(c => c.id === activeId)
    if (!conv) return

    // Find the last user message
    const lastUserMsg = [...conv.messages].reverse().find(m => m.role === 'user')
    if (!lastUserMsg) return

    // Remove the last assistant message
    setConversations(prev =>
      prev.map(c => {
        if (c.id !== activeId) return c
        const msgs = [...c.messages]
        const lastAssistantIdx = msgs.map(m => m.role).lastIndexOf('assistant')
        if (lastAssistantIdx === -1) return c
        msgs.splice(lastAssistantIdx, 1)
        return { ...c, messages: msgs }
      })
    )

    // Re-stream
    const assistantMsgId = uuidv4()
    const assistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      thinking: true,
    }

    // Wait a tick for state to settle
    await new Promise(r => setTimeout(r, 50))

    appendMessage(activeId, assistantMsg)

    cancelRef.current = false
    setIsThinking(true)
    setStreamingId(assistantMsgId)

    await new Promise(r => setTimeout(r, 700))
    if (cancelRef.current) {
      updateMessage(activeId, assistantMsgId, { thinking: false, content: '*Response stopped.*' })
      setStreamingId(null)
      setIsThinking(false)
      return
    }

    setIsThinking(false)
    updateMessage(activeId, assistantMsgId, { thinking: false })

    let accumulated = ''
    await streamResponse(
      lastUserMsg.content,
      (chunk) => {
        accumulated += chunk
        updateMessage(activeId, assistantMsgId, { content: accumulated })
      },
      () => cancelRef.current
    )

    setStreamingId(null)
    cancelRef.current = false
  }, [activeId, conversations, streamingId, appendMessage, updateMessage])

  return {
    conversations,
    activeId,
    activeConversation,
    messages,
    streamingId,
    isThinking,
    isStreaming: !!streamingId,
    newConversation,
    selectConversation,
    deleteConversation,
    renameConversation,
    sendMessage,
    sendImageMessage,
    stopStreaming,
    regenerateLastResponse,
  }
}