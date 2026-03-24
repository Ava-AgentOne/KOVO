import { useState, useEffect, useRef, useCallback } from 'react'
import { RefreshCw } from 'lucide-react'

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="bg-gray-200 dark:bg-gray-700 px-1 rounded text-brand-600 dark:text-yellow-300 text-xs">$1</code>')
    .replace(/\n/g, '<br/>')
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
        isUser
          ? 'bg-brand-500 text-white rounded-br-sm'
          : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-bl-sm border border-gray-200 dark:border-gray-700'
      }`}>
        <p
          className="text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
        />
        {msg.model && (
          <p className="text-xs text-gray-400 mt-1">{msg.model}</p>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-bl-sm px-4 py-3">
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

  useEffect(() => { scrollToBottom() }, [messages, typing])

  const connect = useCallback(() => {
    let ws = null
    let reconnectTimeout = null
    let destroyed = false

    function start() {
      if (destroyed) return
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${proto}//${window.location.host}/api/ws/chat`)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = (event) => {
        setConnected(false)
        if (!destroyed) reconnectTimeout = setTimeout(start, 2000)
      }
      ws.onerror = () => setConnected(false)
      ws.onmessage = (event) => {
        let data
        try { data = JSON.parse(event.data) } catch { return }
        if (data.type === 'history') {
          setMessages(data.messages || [])
        } else if (data.type === 'typing') {
          setTyping(true)
        } else if (data.type === 'message') {
          setTyping(false)
          if (data.role === 'assistant') {
            setMessages(prev => [...prev, { role: data.role, content: data.content, model: data.model }])
          }
        }
      }
    }

    start()
    return () => {
      destroyed = true
      clearTimeout(reconnectTimeout)
      if (ws) { ws.onclose = null; ws.close(); wsRef.current = null }
    }
  }, [])

  useEffect(() => connect(), [connect])

  const reconnect = () => {
    if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close() }
    connect()
  }

  const sendMessage = () => {
    const text = input.trim()
    if (!text || !connected) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    inputRef.current?.focus()
    wsRef.current?.send(JSON.stringify({ message: text }))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Chat with Kovo</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-500">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
          {!connected && (
            <button
              onClick={reconnect}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
              <RefreshCw size={12} /> Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 min-h-0">
        {messages.length === 0 && !typing && (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-400 italic text-sm">No messages yet. Say hi to Kovo!</p>
          </div>
        )}
        {messages.map((msg, i) => <Message key={i} msg={msg} />)}
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
          placeholder={connected ? "Message Kovo… (Enter to send, Shift+Enter for newline)" : "Connecting…"}
          disabled={!connected}
          rows={2}
          className="flex-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 resize-none focus:outline-none focus:border-brand-500 disabled:opacity-50"
        />
        <button
          onClick={sendMessage}
          disabled={!connected || !input.trim()}
          className="bg-brand-500 hover:bg-brand-600 disabled:bg-gray-200 dark:disabled:bg-gray-800 disabled:text-gray-400 text-white px-5 py-2 rounded-xl text-sm font-medium transition-colors self-end"
        >
          Send
        </button>
      </div>
    </div>
  )
}
