import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, FileText, Send, Settings, ShieldCheck, Trash2, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Markdown } from '../components/Markdown'
import { Card, cx, DataBadge, Notice, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol } from '../lib/format'

interface Source { ID: string; Content: string; Source: string; Type: string; Retrieved: string; Link: string | null; excerpt?: string }
interface Msg { role: 'user' | 'assistant'; content: string; meta?: Record<string, unknown>; sources?: Source[] }

const SUGGESTIONS = ['Give me an overview of the company', 'How have revenue and profit grown?', 'Is the balance sheet strong?', 'How good is the cash conversion?',
  'How is it valued?', 'What are the key risks?', 'What is ROCE?', 'Explain the DuPont analysis']

export default function Assistant() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || ''
  const [docIds, setDocIds] = useState<number[]>([])
  const [input, setInput] = useState('')
  const [msgs, setMsgs] = useState<Msg[]>([])
  const end = useRef<HTMLDivElement>(null)
  const settings = useQuery({ queryKey: ['ai-settings'], queryFn: () => api.get<{ provider: string; model?: string }>('/assistant/settings') })
  const docs = useQuery({ queryKey: ['documents'], queryFn: () => api.get<{ id: number; filename: string; symbol: string | null; doc_type: string; period: string; pages: number }[]>('/documents') })
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])
  const ask = useMutation({
    mutationFn: (question: string) => api.post<{ answer: string; meta: Record<string, unknown>; sources: Source[] }>('/assistant/ask', {
      question, symbol: symbol || null, doc_ids: docIds, history: msgs.slice(-6).map((m) => ({ role: m.role, content: m.content })) }),
    onSuccess: (r) => setMsgs((m) => [...m, { role: 'assistant', content: r.answer, meta: r.meta, sources: r.sources }]),
    onError: (e) => setMsgs((m) => [...m, { role: 'assistant', content: `**Error:** ${(e as Error).message}` }]),
  })
  const send = (text: string) => {
    const t = text.trim()
    if (!t || ask.isPending) return
    setMsgs((m) => [...m, { role: 'user', content: t }])
    setInput('')
    ask.mutate(t)
  }
  const engine = settings.data?.provider === 'anthropic' ? `Claude API (${settings.data.model ?? ''})` : settings.data?.provider === 'ollama' ? 'Ollama (local)' : 'Offline analyst (free)'
  const relevantDocs = (docs.data ?? []).filter((d) => !symbol || !d.symbol || d.symbol === symbol)

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="AI research assistant" title="Ask about companies, statements, valuation and documents"
        subtitle="Answers use only EquityPilot's stored data, your notes and your selected documents - each fact cites a numbered source, and interpretation is labelled separately. The assistant does not give buy/sell recommendations." />
      <div className="grid gap-5 xl:grid-cols-4">
        <div className="space-y-4">
          <Card title="Context">
            <label className="label">Company</label>
            <CompanyPicker value={symbol} onChange={(s) => setParams({ symbol: s })} />
            {symbol && <div className="mt-2 flex items-center justify-between text-sm"><Link className="font-medium text-brand-600 hover:underline" to={`/company/${encodeURIComponent(symbol)}`}>{baseSymbol(symbol)}</Link><button className="text-xs muted" onClick={() => setParams({})}>Clear</button></div>}
            <label className="label mt-4">Documents ({relevantDocs.length})</label>
            {relevantDocs.length === 0 ? <p className="text-xs muted">Upload annual reports or results in <Link className="text-brand-600 underline" to="/documents">Documents</Link> to ask about them.</p> : (
              <ul className="space-y-1">{relevantDocs.map((d) => (
                <li key={d.id}><label className="flex cursor-pointer items-start gap-2 rounded-lg p-1.5 text-sm hover:bg-slate-100 dark:hover:bg-ink-700">
                  <input type="checkbox" className="mt-1" checked={docIds.includes(d.id)} onChange={() => setDocIds((s) => (s.includes(d.id) ? s.filter((x) => x !== d.id) : [...s, d.id]))} />
                  <span className="min-w-0"><span className="block truncate font-medium">{d.filename}</span><span className="text-xs muted">{d.doc_type} · {d.period} · {d.pages} pp</span></span></label></li>))}</ul>
            )}
          </Card>
          <Card title="Engine">
            <div className="flex items-center gap-2 text-sm"><Bot className="h-4 w-4 text-brand-600" />{engine}</div>
            <p className="mt-1 text-xs muted">{settings.data?.provider === 'offline' || !settings.data ? 'Deterministic and free: quotes facts and calculations from the sources. Connect Claude or Ollama in Settings for written explanations.' : 'Answers are checked: figures not found in the sources are flagged.'}</p>
            <Link to="/settings" className="btn-ghost mt-2 px-0"><Settings className="h-4 w-4" />AI settings & costs</Link>
          </Card>
        </div>
        <div className="xl:col-span-3">
          <div className="card flex h-[calc(100vh-15rem)] min-h-[520px] flex-col">
            <div className="flex-1 space-y-5 overflow-y-auto p-5">
              {msgs.length === 0 && (
                <div className="mx-auto max-w-xl py-8 text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white"><Bot className="h-6 w-6" /></div>
                  <h2 className="mt-3 text-lg font-semibold">How can I help with your research?</h2>
                  <p className="mt-1 text-sm muted">{symbol ? `Context: ${baseSymbol(symbol)}${docIds.length ? ` + ${docIds.length} document(s)` : ''}` : 'Pick a company for company questions, or ask about a finance concept.'}</p>
                  <div className="mt-4 flex flex-wrap justify-center gap-2">{(docIds.length ? ['Summarise the key points of this document', 'What does the report say about risks?', ...SUGGESTIONS.slice(0, 3)] : SUGGESTIONS).map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>
                  <Notice className="mt-6 text-left"><ShieldCheck className="mr-1 inline h-4 w-4 text-up" />Facts are quoted from cited sources; calculations show their formula; interpretations are labelled. Missing information is stated, never invented.</Notice>
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={cx('flex gap-3', m.role === 'user' && 'flex-row-reverse')}>
                  <div className={cx('flex h-8 w-8 shrink-0 items-center justify-center rounded-xl', m.role === 'user' ? 'bg-slate-200 dark:bg-ink-700' : 'bg-brand-600 text-white')}>
                    {m.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}</div>
                  <div className={cx('max-w-[85%] rounded-2xl px-4 py-3', m.role === 'user' ? 'bg-brand-600 text-white' : 'bg-slate-50 dark:bg-ink-800')}>
                    {m.role === 'user' ? <p className="text-sm">{m.content}</p> : <Markdown text={m.content} />}
                    {m.meta && (
                      <div className="mt-3 border-t border-slate-200 pt-2 text-[11px] muted dark:border-ink-600">
                        Engine: {String(m.meta.engine)}
                        {m.meta.grounding ? <> · Grounding: {(m.meta.grounding as { figures: number; untraced: string[] }).figures - (m.meta.grounding as { untraced: string[] }).untraced.length}/{(m.meta.grounding as { figures: number }).figures} figures traced to sources{(m.meta.grounding as { untraced: string[] }).untraced.length ? ` (check: ${(m.meta.grounding as { untraced: string[] }).untraced.join(', ')})` : ''}</> : null}
                        {m.meta.cost_usd ? <> · est. cost ${Number(m.meta.cost_usd).toFixed(4)}</> : null}
                        {m.meta.warning ? <> · {String(m.meta.warning)}</> : null}
                      </div>
                    )}
                    {m.sources && m.sources.length > 0 && (
                      <details className="mt-2"><summary className="cursor-pointer text-xs font-medium text-brand-600 dark:text-brand-300">Sources used ({m.sources.length})</summary>
                        <ul className="mt-2 space-y-1.5">{m.sources.map((s) => (
                          <li key={s.ID} className="rounded-lg bg-white p-2 text-xs dark:bg-ink-900"><b>[{s.ID}]</b> {s.Content} <DataBadge type={s.Type.toLowerCase().includes('sample') ? 'sample' : s.Type.toLowerCase().includes('upload') ? 'official_upload' : s.Type.toLowerCase().includes('calc') ? 'calculated' : 'third_party'} />
                            <div className="muted">{s.Source}{s.Retrieved && s.Retrieved !== '—' ? ` · ${s.Retrieved}` : ''}</div>
                            {s.excerpt && <div className="mt-1 italic muted"><FileText className="mr-1 inline h-3 w-3" />"{s.excerpt}…"</div>}</li>))}</ul></details>
                    )}
                  </div>
                </div>
              ))}
              {ask.isPending && <div className="flex gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white"><Bot className="h-4 w-4" /></div><div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm muted dark:bg-ink-800">Gathering sources and drafting…</div></div>}
              <div ref={end} />
            </div>
            <form className="flex gap-2 border-t border-slate-200 p-3 dark:border-ink-700" onSubmit={(e) => { e.preventDefault(); send(input) }}>
              {msgs.length > 0 && <button type="button" className="btn-ghost p-2" onClick={() => setMsgs([])} aria-label="Clear conversation"><Trash2 className="h-4 w-4" /></button>}
              <input className="input flex-1" placeholder={symbol ? `Ask about ${baseSymbol(symbol)}…` : 'Ask about a company or concept…'} value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} />
              <button className="btn-primary" disabled={!input.trim() || ask.isPending}><Send className="h-4 w-4" />Ask</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
