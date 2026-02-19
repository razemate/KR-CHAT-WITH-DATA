'use client'

import { useMemo, useRef, useState } from 'react'

function Table({ columns, rows }) {
  if (!columns?.length) return null
  return (
    <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: 12 }}>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} style={{ textAlign: 'left', padding: 10, borderBottom: '1px solid #e5e7eb', background: '#fafafa', fontSize: 12 }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={idx}>
              {r.map((v, j) => (
                <td key={j} style={{ padding: 10, borderBottom: '1px solid #f1f5f9', fontSize: 13, whiteSpace: 'nowrap' }}>
                  {String(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Page() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'KR DATA CHAT ready. Ask a question about your data.' }
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef(null)

  const canSend = useMemo(() => input.trim().length > 0 && !busy, [input, busy])

  async function send() {
    if (!canSend) return
    const text = input.trim()
    setInput('')
    setBusy(true)

    setMessages((m) => [...m, { role: 'user', content: text }])

    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })

      const data = await r.json()
      if (!r.ok) throw new Error(data?.detail || 'Request failed')

      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: '',
          sql: data.sql,
          columns: data.columns,
          rows: data.rows
        }
      ])
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: Error:  }])
    } finally {
      setBusy(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#ffffff' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #e5e7eb', fontWeight: 600 }}>
          KR DATA CHAT
        </div>

        {/* Messages (vertical stacked) */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
          {messages.map((m, i) => (
            <div key={i} style={{ display: 'flex', marginBottom: 14, justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div
                style={{
                  maxWidth: 920,
                  width: 'fit-content',
                  padding: 14,
                  borderRadius: 14,
                  background: m.role === 'user' ? '#111827' : '#f3f4f6',
                  color: m.role === 'user' ? '#ffffff' : '#111827',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.4
                }}
              >
                {m.content ? <div>{m.content}</div> : null}

                {m.sql ? (
                  <div style={{ marginTop: 10, fontSize: 12, opacity: 0.9 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>SQL</div>
                    <div style={{ background: '#ffffff', color: '#111827', padding: 10, borderRadius: 10, border: '1px solid #e5e7eb', overflowX: 'auto' }}>
                      {m.sql}
                    </div>
                  </div>
                ) : null}

                {m.columns?.length ? (
                  <div style={{ marginTop: 10 }}>
                    <Table columns={m.columns} rows={m.rows || []} />
                  </div>
                ) : null}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div style={{ padding: 16, borderTop: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', gap: 10, maxWidth: 980, margin: '0 auto' }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder='Message KR DATA CHAT...'
              rows={1}
              style={{
                flex: 1,
                resize: 'none',
                padding: 12,
                borderRadius: 14,
                border: '1px solid #e5e7eb',
                outline: 'none',
                fontSize: 14
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
            />
            <button
              onClick={send}
              disabled={!canSend}
              style={{
                padding: '0 16px',
                borderRadius: 14,
                border: '1px solid #e5e7eb',
                background: canSend ? '#111827' : '#f3f4f6',
                color: canSend ? '#ffffff' : '#9ca3af',
                fontWeight: 600,
                cursor: canSend ? 'pointer' : 'not-allowed'
              }}
            >
              {busy ? '...' : 'Send'}
            </button>
          </div>
          <div style={{ maxWidth: 980, margin: '10px auto 0', fontSize: 12, color: '#6b7280' }}>
            Enter = send • Shift+Enter = new line
          </div>
        </div>
      </div>
    </div>
  )
}
