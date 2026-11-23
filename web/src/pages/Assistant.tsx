import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Bot, Check, Copy, FileText, Loader2, RotateCcw, Send, Settings, ShieldCheck, Sparkles, Square, Trash2, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Markdown } from '../components/Markdown'
import { Card, cx, DataBadge, Notice, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol } from '../lib/format'

interface Source { ID: string; Content: string; Source: string; Type: string; Retrieved: string; Link: string | null; excerpt?: string }
interface Grounding { figures: number; untraced: string[]; calculated?: string[]; unknown_citations?: string[]; uncited_lines?: number }
interface Meta { engine?: string; grounding?: Grounding | null; cost_usd?: number | null; warning?: string; note?: string | null; seconds?: number; steps?: number; prefetched?: number }
interface Msg { role: 'user' | 'assistant'; content: string; steps?: string[]; notes?: string[]; meta?: Meta; sources?: Source[]; streaming?: boolean; question?: string; error?: boolean }

const GENERAL = ['What is happening in Indian markets?', 'Compare TCS and Infosys', 'Which companies have ROE above 20%?', 'Explain Reliance Industries in simple English',
  'Show the revenue growth of HDFC Bank', 'Latest RBI news', 'Explain DCF valuation', 'Which companies are debt free?']
const COMPANY = ['Explain this company in simple English', 'Explain the latest quarterly results', 'How have revenue and profit grown?', 'What is the debt-to-equity ratio?',
  'How is it valued?', 'What are the major risks?', 'Latest news']
const STORE = 'ep-assistant-conversation'

function typeBadge(t: string) {
  const s = t.toLowerCase()
  return s.includes('sample') ? 'sample' : s.includes('upload') ? 'official_upload' : s.includes('calc') ? 'calculated' : s.includes('live') ? 'live'
    : s.includes('delayed') ? 'delayed' : s.includes('official') ? 'official' : 'third_party'
}

/** The last conversation is kept in this browser only (per-viewer convenience; nothing is sent anywhere). */
function loadConversation(): Msg[] {
  try {
    const raw = localStorage.getItem(STORE)
    const v = raw ? JSON.parse(raw) : []
    return Array.isArray(v) ? (v as Msg[]).filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string').slice(-30) : []
  } catch { return [] }
}
function saveConversation(msgs: Msg[]) {
  try {
    const done = msgs.filter((m) => !m.streaming).slice(-30)
    if (done.length) localStorage.setItem(STORE, JSON.stringify(done)); else localStorage.removeItem(STORE)
  } catch { /* storage unavailable (private window) - the conversation simply is not kept */ }
}

/** POST a question and read the server-sent events (status / delta / interim / reset / final). */
async function streamAsk(body: unknown, signal: AbortSignal, on: (ev: { type: string; text?: string; meta?: Meta; sources?: Source[] }) => void) {
  const res = await fetch('/api/assistant/stream', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal })
  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`
    try { detail = (await res.json()).detail ?? detail } catch { /* not JSON */ }
    throw new Error(detail)
  }
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, i)
      buf = buf.slice(i + 2)
      const line = frame.split('\n').find((l) => l.startsWith('data: '))
      if (line) { try { on(JSON.parse(line.slice(6))) } catch { /* ignore partial frame */ } }
    }
  }
}

function CopyButton({ text }: { text: string }) {
  const [ok, setOk] = useState(false)
  return (
    <button type="button" className="inline-flex items-center gap-1 text-[11px] muted hover:text-brand-600" onClick={() => { navigator.clipboard?.writeText(text); setOk(true); window.setTimeout(() => setOk(false), 1500) }}>
      {ok ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}{ok ? 'Copied' : 'Copy answer'}
    </button>
  )
}

function Steps({ steps, active }: { steps: string[]; active: boolean }) {
  if (!steps.length) return active ? <div className="flex items-center gap-2 text-xs muted"><Loader2 className="h-3.5 w-3.5 animate-spin" />Understanding the question…</div> : null
  return (
    <ul className="mb-2 space-y-1 text-xs">
      {steps.map((s, k) => {
        const running = active && k === steps.length - 1
        return <li key={k} className="flex items-center gap-2 muted">{running ? <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-500" /> : <Check className="h-3.5 w-3.5 text-up" />}{s}</li>
      })}
    </ul>
  )
}

/** Shown with the answer whenever the automatic check found something to verify - never hidden in a tooltip. */
function GroundingNotice({ g }: { g: Grounding }) {
  const unknown = g.unknown_citations ?? []
  if (!g.untraced.length && !unknown.length) return null
  return (
    <div className="mt-3 flex gap-2 rounded-lg border border-saffron-500/40 bg-amber-50/70 px-3 py-2 text-xs dark:bg-saffron-500/10" role="note">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-saffron-500" />
      <div className="space-y-0.5">
        {g.untraced.length > 0 && <p><b>Check these figures:</b> {g.untraced.join(', ')} - they were not found in the data the assistant read. Verify them before relying on them.</p>}
        {unknown.length > 0 && <p><b>Unknown source tags:</b> {unknown.join(', ')} - the answer cites sources that were not retrieved.</p>}
      </div>
    </div>
  )
}

export default function Assistant() {
  const [params, setParams] = useSearchParams()
  const symbol = params.get('symbol') || ''
  const [docIds, setDocIds] = useState<number[]>([])
  const [input, setInput] = useState('')
  const [msgs, setMsgs] = useState<Msg[]>(loadConversation)
  const [busy, setBusy] = useState(false)
  const [openSrc, setOpenSrc] = useState<{ msg: number; id: string } | null>(null)
  const abort = useRef<AbortController | null>(null)
  const end = useRef<HTMLDivElement>(null)
  const sentQ = useRef<string | null>(null)
  const settings = useQuery({ queryKey: ['ai-settings'], queryFn: () => api.get<{ provider: string; model?: string }>('/assistant/settings') })
  const docs = useQuery({ queryKey: ['documents'], queryFn: () => api.get<{ id: number; filename: string; symbol: string | null; doc_type: string; period: string; pages: number }[]>('/documents') })
  const lastContent = msgs[msgs.length - 1]?.content
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [msgs.length, lastContent])
  useEffect(() => { if (!busy) saveConversation(msgs) }, [msgs, busy])
  useEffect(() => {          // a clicked source tag: open the list and bring that source into view
    if (!openSrc) return
    document.getElementById(`src-${openSrc.msg}-${openSrc.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [openSrc])

  const patchLast = (fn: (m: Msg) => Msg) => setMsgs((all) => all.map((m, k) => (k === all.length - 1 ? fn(m) : m)))

  const send = async (text: string, base: Msg[] = msgs) => {
    const t = text.trim()
    if (!t || busy) return
    const history = base.filter((m) => m.content && !m.streaming && !m.error).slice(-6).map((m) => ({ role: m.role, content: m.content }))
    setMsgs([...base, { role: 'user', content: t }, { role: 'assistant', content: '', steps: [], notes: [], streaming: true, question: t }])
    setInput('')
    setBusy(true)
    setOpenSrc(null)
    const ctl = new AbortController()
    abort.current = ctl
    try {
      await streamAsk({ question: t, symbol: symbol || null, doc_ids: docIds, history }, ctl.signal, (ev) => {
        if (ev.type === 'status') patchLast((m) => ({ ...m, steps: [...(m.steps ?? []), ev.text ?? ''] }))
        else if (ev.type === 'delta') patchLast((m) => ({ ...m, content: m.content + (ev.text ?? '') }))
        else if (ev.type === 'interim') patchLast((m) => ({ ...m, content: '', notes: [...(m.notes ?? []), (ev.text ?? '').trim()].filter(Boolean) }))
        else if (ev.type === 'reset') patchLast((m) => ({ ...m, content: '' }))
        else if (ev.type === 'final') patchLast((m) => ({ ...m, content: ev.text || m.content, meta: ev.meta, sources: ev.sources, streaming: false }))
      })
    } catch (e) {
      const aborted = (e as Error).name === 'AbortError'
      patchLast((m) => ({ ...m, streaming: false, error: true, content: m.content + (aborted ? '\n\n*Stopped.*' : `\n\n**Error:** ${(e as Error).message}`) }))
    } finally {
      patchLast((m) => (m.streaming ? { ...m, streaming: false } : m))
      setBusy(false)
      abort.current = null
    }
  }
  const retry = (i: number) => {
    const q = msgs[i]?.question
    if (q) send(q, msgs.slice(0, i - 1))      // drop the failed question and answer, ask again with the earlier history
  }

  // questions handed over from elsewhere (Home "Ask AI", company pages): /assistant?q=...
  useEffect(() => {
    const q = params.get('q')
    if (q && sentQ.current !== q) {
      sentQ.current = q
      const next = new URLSearchParams(params)
      next.delete('q')
      setParams(next, { replace: true })
      send(q)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  const provider = settings.data?.provider
  const engine = provider === 'anthropic' ? `Claude (${settings.data?.model ?? ''})` : provider === 'ollama' ? 'Ollama (local model)' : 'Offline analyst (free)'
  const relevantDocs = (docs.data ?? []).filter((d) => !symbol || !d.symbol || d.symbol === symbol)
  const suggestions = docIds.length ? ['Summarise this document', 'What does the report say about risks?', 'What does it say about revenue growth?', ...COMPANY.slice(0, 2)]
    : symbol ? COMPANY : GENERAL

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="AI research assistant" title="Ask about companies, the market, comparisons and filings"
        subtitle="The assistant looks things up in EquityPilot's data (financials, prices, news, your documents) and cites every fact. Interpretation is labelled separately, and it never gives buy/sell recommendations." />
      <div className="grid gap-5 xl:grid-cols-4">
        <div className="order-last space-y-4 xl:order-none">
          <Card title="Context (optional)">
            <label className="label">Company</label>
            <CompanyPicker value={symbol} onChange={(s) => setParams({ symbol: s })} />
            {symbol ? <div className="mt-2 flex items-center justify-between text-sm"><Link className="font-medium text-brand-600 hover:underline" to={`/company/${encodeURIComponent(symbol)}`}>{baseSymbol(symbol)}</Link><button className="text-xs muted" onClick={() => setParams({})}>Clear</button></div>
              : <p className="mt-2 text-xs muted">Not required - you can name companies in your question ("Compare TCS and Infosys"), and follow-up questions ("what about its debt?") continue with the same company.</p>}
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
            <p className="mt-1 text-xs muted">{provider === 'anthropic'
              ? 'EquityPilot first fetches the data your question needs, then Claude writes a cited answer and looks up anything else it needs. Figures not found in the data are flagged with the answer.'
              : 'Free and private: answers market, comparison, screening, news, company and concept questions from the data with rules. Connect Claude in Settings for written, multi-step analysis.'}</p>
            <Link to="/settings" className="btn-ghost mt-2 px-0"><Settings className="h-4 w-4" />AI settings & costs</Link>
          </Card>
        </div>
        <div className="xl:col-span-3">
          <div className="card flex h-[calc(100dvh-17rem)] min-h-[480px] flex-col lg:h-[calc(100dvh-15rem)]">
            <div className="flex-1 space-y-5 overflow-y-auto p-3 sm:p-5" aria-live="polite">
              {msgs.length === 0 && (
                <div className="mx-auto max-w-2xl py-6 text-center sm:py-10">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-500/25"><Sparkles className="h-6 w-6" /></div>
                  <h2 className="mt-3 text-lg font-semibold">What would you like to research?</h2>
                  <p className="mt-1 text-sm muted">{symbol ? `Context: ${baseSymbol(symbol)}${docIds.length ? ` + ${docIds.length} document(s)` : ''}` : 'Ask about any listed company, compare companies, screen the market or learn a concept - in your own words.'}</p>
                  <div className="mt-4 flex flex-wrap justify-center gap-2">{suggestions.map((s) => <button key={s} className="chip" onClick={() => send(s)}>{s}</button>)}</div>
                  <Notice className="mt-6 text-left"><ShieldCheck className="mr-1 inline h-4 w-4 text-up" />Answers start with a direct answer, then the figures with source tags like <span className="rounded bg-brand-50 px-1 text-[10px] font-semibold text-brand-700 dark:bg-brand-500/15 dark:text-brand-200">T2</span> (click one to see the source), calculations with their formula, a plain-English reading and the reporting periods. Missing information is stated, never invented. Educational only - not investment advice.</Notice>
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={cx('flex gap-2.5 sm:gap-3', m.role === 'user' && 'flex-row-reverse')}>
                  <div className={cx('flex h-8 w-8 shrink-0 items-center justify-center rounded-xl', m.role === 'user' ? 'bg-slate-200 dark:bg-ink-700' : 'bg-brand-600 text-white')}>
                    {m.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}</div>
                  <div className={cx('min-w-0 rounded-2xl px-3.5 py-3 sm:px-4', m.role === 'user' ? 'max-w-[85%] bg-brand-600 text-white' : 'w-full max-w-[min(100%,52rem)] bg-slate-50 dark:bg-ink-800')}>
                    {m.role === 'user' ? <p className="text-sm">{m.content}</p> : (<>
                      <Steps steps={m.steps ?? []} active={!!m.streaming && !m.content} />
                      {(m.notes ?? []).length > 0 && <div className="mb-2 border-l-2 border-slate-200 pl-2 text-xs italic muted dark:border-ink-600">{m.notes!.join(' ')}</div>}
                      {m.content && <div className={cx(m.streaming && 'caret')}><Markdown text={m.content} onCite={m.sources?.length ? (id) => setOpenSrc({ msg: i, id }) : undefined} /></div>}
                      {m.meta?.grounding && <GroundingNotice g={m.meta.grounding} />}
                    </>)}
                    {m.role === 'assistant' && !m.streaming && (m.meta || m.error) && (
                      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-200 pt-2 text-[11px] muted dark:border-ink-600">
                        {m.meta?.engine && <span>Engine: {m.meta.engine}</span>}
                        {m.meta?.seconds != null && <span>{m.meta.seconds}s</span>}
                        {m.meta?.grounding && m.meta.grounding.figures > 0 && (() => {
                          const g = m.meta.grounding, calc = g.calculated?.length ?? 0, traced = g.figures - g.untraced.length - calc
                          return <span title="Automatic check of every figure in the answer against the data the assistant read">
                            Figures: {traced}/{g.figures} found in the data{calc ? `, ${calc} calculated` : ''}{g.untraced.length ? `, ${g.untraced.length} to check` : ' ✓'}</span>
                        })()}
                        {m.meta?.cost_usd ? <span title="Estimated from the token counts the API reported, at list prices">est. API cost ${Number(m.meta.cost_usd).toFixed(4)}</span> : null}
                        {m.meta?.note && <span>{m.meta.note}</span>}
                        {m.meta?.warning && <span className="text-saffron-500">{m.meta.warning}</span>}
                        <span className="ml-auto flex items-center gap-3">
                          {m.error && m.question && i === msgs.length - 1 && <button type="button" className="inline-flex items-center gap-1 text-[11px] font-medium text-brand-600 hover:underline dark:text-brand-300" onClick={() => retry(i)}><RotateCcw className="h-3 w-3" />Retry</button>}
                          {m.content && <CopyButton text={m.content} />}
                        </span>
                      </div>
                    )}
                    {m.sources && m.sources.length > 0 && (
                      <details className="mt-2" open={openSrc?.msg === i || undefined}><summary className="cursor-pointer text-xs font-medium text-brand-600 dark:text-brand-300">Sources used ({m.sources.length})</summary>
                        <ul className="mt-2 space-y-1.5">{m.sources.map((s) => (
                          <li key={s.ID} id={`src-${i}-${s.ID}`} className={cx('rounded-lg bg-white p-2 text-xs transition-shadow dark:bg-ink-900', openSrc?.msg === i && openSrc.id === s.ID && 'ring-2 ring-brand-500')}>
                            <b>[{s.ID}]</b> {s.Link ? <a className="hover:underline" href={s.Link} target="_blank" rel="noopener noreferrer">{s.Content}</a> : s.Content} <DataBadge type={typeBadge(s.Type)} />
                            <div className="muted">{s.Source}{s.Retrieved && s.Retrieved !== '—' ? ` · ${s.Retrieved}` : ''}</div>
                            {s.excerpt && <div className="mt-1 italic muted"><FileText className="mr-1 inline h-3 w-3" />"{s.excerpt}…"</div>}</li>))}</ul></details>
                    )}
                  </div>
                </div>
              ))}
              <div ref={end} />
            </div>
            <form className="flex gap-2 border-t border-slate-200 p-2.5 sm:p-3 dark:border-ink-700" onSubmit={(e) => { e.preventDefault(); send(input) }}>
              {msgs.length > 0 && !busy && <button type="button" className="btn-ghost p-2" onClick={() => setMsgs([])} aria-label="Clear conversation" title="New conversation"><Trash2 className="h-4 w-4" /></button>}
              <input className="input flex-1" placeholder={symbol ? `Ask about ${baseSymbol(symbol)}, or anything else…` : 'Ask about a company, a comparison, the market…'} value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} aria-label="Your question" />
              {busy ? <button type="button" className="btn-outline" onClick={() => abort.current?.abort()}><Square className="h-4 w-4" />Stop</button>
                : <button className="btn-primary" disabled={!input.trim()}><Send className="h-4 w-4" /><span className="hidden sm:inline">Ask</span></button>}
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
