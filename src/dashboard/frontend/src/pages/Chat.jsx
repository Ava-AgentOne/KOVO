import { useState, useEffect, useRef, useCallback } from 'react'

// Simple markdown-like renderer for bold, code, and line breaks
function renderMarkdown(text) {
  if (!text) return ''
  // Replace **bold** with <strong>
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="bg-gray-700 px-1 rounded text-yellow-300 text-xs">$1</code>')
    .replace(/\n/g, '<br/>')
  return html
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
        isUser
          ? 'bg-brand-600 text-white rounded-br-sm'
          : 'bg-gray-800 text-gray-100 rounded-bl-sm border border-gray-700'
      }`}>
        <p
          className="text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
        />
        {msg.model && (
          <p className="text-xs text-gray-500 mt-1">{msg.model}</p>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-sm px-4 py-3">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'0ms'}}/>
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'150ms'}}/>
          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay:'300ms'}}/>
        </div>
      </div>
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [typing, setTyping] = useState(false)
  const wsRef = useRef(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, typing])

  useEffect(() => {
    // Use closure variables — safer than refs for effect lifecycle management.
    let ws = null
    let reconnectTimeout = null
    let destroyed = false

    function connect() {
      if (destroyed) return
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${proto}//${window.location.host}/api/ws/chat`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[Chat] WebSocket opened')
        setConnected(true)
      }

      ws.onclose = (event) => {
        console.warn('[Chat] WebSocket closed — code:', event.code, '| reason:', event.reason || '(none)', '| wasClean:', event.wasClean)
        setConnected(false)
        if (!destroyed) {
          reconnectTimeout = setTimeout(connect, 2000)
        }
      }

      ws.onerror = (event) => {
        console.error('[Chat] WebSocket error', event)
        setConnected(false)
      }

      ws.onmessage = (event) => {
        let data
        try {
          data = JSON.parse(event.data)
        } catch (e) {
          console.error('[Chat] WS JSON parse error', e, event.data)
          return
        }

        if (data.type === 'history') {
          setMessages(data.messages || [])
        } else if (data.type === 'typing') {
          setTyping(true)
        } else if (data.type === 'message') {
          setTyping(false)
          // Don't re-add user messages we already added optimistically
          if (data.role === 'assistant') {
            setMessages(prev => [...prev, { role: data.role, content: data.content, model: data.model }])
          }
        }
      }
    }

    connect()

    return () => {
      console.log('[Chat] effect cleanup — destroying WebSocket')
      destroyed = true
      clearTimeout(reconnectTimeout)
      if (ws) {
        ws.onclose = null  // prevent reconnect loop from the close we're about to trigger
        ws.close()
        wsRef.current = null
      }
    }
  }, [])

  const sendMessage = () => {
    const text = input.trim()
    if (!text || !connected) return

    // Optimistic UI: add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    inputRef.current?.focus()

    wsRef.current?.send(JSON.stringify({ message: text }))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold text-white">Chat with MiniClaw</h1>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-sm text-gray-400">{connected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-gray-900 border border-gray-800 rounded-lg p-4 min-h-0">
        {messages.length === 0 && !typing && (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-600 italic text-sm">No messages yet. Say hi to MiniClaw!</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {typing && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 mt-4 flex-shrink-0">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={connected ? "Message MiniClaw… (Enter to send, Shift+Enter for newline)" : "Connecting…"}
          disabled={!connected}
          rows={2}
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-600 resize-none focus:outline-none focus:border-brand-500 disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={!connected || !input.trim()}
          className="bg-brand-600 hover:bg-brand-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors self-end"
        >
          Send
        </button>
      </div>
    </div>
  )
}
