import { useState, useEffect, useRef, useCallback } from 'react'
import { RefreshCw, Trash2, ArrowDown, MessageSquare } from 'lucide-react'

function renderMarkdown(text) {
  if (!text) return ''
  return text
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Code blocks (``` ... ```)
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-2 my-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap border border-gray-200 dark:border-gray-700"><code>${code.trim()}</code></pre>`)
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-brand-600 dark:text-yellow-300 text-xs font-mono">$1</code>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // Links
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer" class="text-brand-500 hover:text-brand-600 underline underline-offset-2">$1</a>')
    // Bare URLs
    .replace(/(^|[^"'])(https?:\/\/[^\s<]+)/g, '$1<a href="$2" target="_blank" rel="noreferrer" class="text-brand-500 hover:text-brand-600 underline underline-offset-2 break-all">$2</a>')
    // Headers (## and #)
    .replace(/^### (.+)$/gm, '<p class="font-semibold text-gray-800 dark:text-gray-200 mt-2 mb-0.5 text-sm">$1</p>')
    .replace(/^## (.+)$/gm, '<p class="font-bold text-gray-800 dark:text-gray-200 mt-2 mb-0.5">$1</p>')
    .replace(/^# (.+)$/gm, '<p class="font-bold text-gray-900 dark:text-white mt-2 mb-1 text-base">$1</p>')
    // Unordered lists
    .replace(/^[-*] (.+)$/gm, '<div class="flex gap-1.5 ml-1"><span class="text-gray-400 flex-shrink-0">•</span><span>$1</span></div>')
    // Numbered lists
    .replace(/^(\d+)\. (.+)$/gm, '<div class="flex gap-1.5 ml-1"><span class="text-gray-400 flex-shrink-0 font-mono text-xs">$1.</span><span>$2</span></div>')
    // Newlines (but not inside pre blocks)
    .replace(/\n/g, '<br/>')
    // Clean up: remove <br/> right after/before block elements
    .replace(/<br\/>(<pre|<\/pre>|<div|<\/div>|<p )/g, '$1')
    .replace(/(<\/pre>|<\/div>|<\/p>)<br\/>/g, '$1')
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3 group`}>
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${
        isUser
          ? 'bg-brand-500 text-white rounded-br-sm'
          : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-bl-sm border border-gray-200 dark:border-gray-700'
      }`}>
        <div
          className="text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
        />
        <div className={`flex items-center gap-2 mt-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {time && (
            <span className={`text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ${
              isUser ? 'text-white/60' : 'text-gray-400'
            }`}>{time}</span>
          )}
          {msg.model && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-200/50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 font-mono">
              {msg.model}
            </span>
          )}
        </div>
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

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
      <div className="w-14 h-14 bg-brand-50 dark:bg-brand-900/20 rounded-2xl flex items-center justify-center">
        <MessageSquare size={24} className="text-brand-500" />
      </div>
      <div>
        <p className="text-gray-500 text-sm font-medium">Start a conversation</p>
        <p className="text-gray-400 text-xs mt-1">This is a backup chat — same Kovo agent as Telegram</p>
      </div>
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [typing, setTyping] = useState(false)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const wsRef = useRef(null)
  const bottomRef = useRef(null)
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollToBottom() }, [messages, typing])

  // Track scroll position to show/hide scroll-to-bottom button
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 100)
  }, [])

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
      ws.onclose = () => {
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
            setMessages(prev => [...prev, {
              role: data.role,
              content: data.content,
              model: data.model,
              timestamp: new Date().toISOString(),
            }])
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

  const clearChat = async () => {
    setMessages([])
    // Also clear server-side history
    try { await fetch('/api/chat/clear', { method: 'POST' }) } catch {}
  }

  const sendMessage = () => {
    const text = input.trim()
    if (!text || !connected) return
    setMessages(prev => [...prev, {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }])
    setInput('')
    // Reset textarea height
    if (inputRef.current) inputRef.current.style.height = 'auto'
    inputRef.current?.focus()
    wsRef.current?.send(JSON.stringify({ message: text }))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  // Auto-grow textarea
  const handleInputChange = (e) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 150) + 'px'
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Chat</h1>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              title="Clear chat"
            >
              <Trash2 size={13} /> Clear
            </button>
          )}
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className="text-xs text-gray-500">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
          {!connected && (
            <button
              onClick={reconnect}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white transition-colors"
            >
              <RefreshCw size={12} /> Reconnect
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 min-h-0 relative"
      >
        {messages.length === 0 && !typing && <EmptyState />}
        {messages.map((msg, i) => <Message key={i} msg={msg} />)}
        {typing && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Scroll-to-bottom FAB */}
      {showScrollBtn && (
        <div className="relative">
          <button
            onClick={scrollToBottom}
            className="absolute -top-12 right-4 w-8 h-8 rounded-full bg-brand-500 hover:bg-brand-600 text-white shadow-lg flex items-center justify-center transition-all hover:scale-110"
          >
            <ArrowDown size={16} />
          </button>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 mt-3 flex-shrink-0">
        <textarea
          ref={inputRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={connected ? "Message Kovo… (Enter to send)" : "Connecting…"}
          disabled={!connected}
          rows={1}
          className="flex-1 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 resize-none focus:outline-none focus:border-brand-500 disabled:opacity-50 overflow-hidden"
          style={{ minHeight: '42px', maxHeight: '150px' }}
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
