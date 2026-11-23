import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bot, Database, Download, ExternalLink, KeyRound, LogIn, LogOut, Moon, Palette, Sun, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Card, cx, DataBadge, Loading, Notice, PageHeader, Segmented, useToast } from '../components/ui'
import { api } from '../lib/api'
import { ist } from '../lib/format'
import { useMe, useTheme } from '../lib/hooks'

interface AISettings {
  provider: 'offline' | 'anthropic' | 'ollama'; model?: string | null; consent?: boolean; ollama_host?: string | null; ollama_model?: string | null; effort?: string | null
  key_configured: boolean; models: Record<string, { label: string; in: number; out: number }>; pricing_note: string
  estimates: Record<string, { company: number; document: number }>
}
interface Sources {
  sources: { name: string; url: string; use: string; access: string }[]
  feeds: Record<string, { source: string; last_refreshed: string | null }>
  companies_tracked: number; securities_listed: number; offline: boolean; realtime_note: string
}

export default function Settings() {
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="My space" title="Settings" subtitle="Your profile and account, appearance, the AI engine and its costs, data sources and your data." />
      <div className="grid gap-5 xl:grid-cols-2">
        <div className="space-y-5"><ProfileCard /><AccountCard /><AppearanceCard /></div>
        <div className="space-y-5"><AICard /><DataCard /></div>
      </div>
    </div>
  )
}

function ProfileCard() {
  const me = useMe()
  const user = me.data?.user
  const [name, setName] = useState('')
  const [board, setBoard] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()
  useEffect(() => { if (user) { setName(user.display_name); setBoard(user.show_on_leaderboard) } }, [user])
  const save = useMutation({
    mutationFn: () => api.patch('/me', { display_name: name.trim(), show_on_leaderboard: board }),
    onSuccess: () => { toast('Profile saved'); qc.invalidateQueries({ queryKey: ['me'] }); qc.invalidateQueries({ queryKey: ['leaderboard'] }) },
    onError: (e) => toast((e as Error).message, 'error'),
  })
  if (!user) return <Card title="Profile"><Loading /></Card>
  return (
    <Card title={<span className="inline-flex items-center gap-1.5"><UserRound className="h-4 w-4 text-brand-600" />Profile</span>}>
      <label className="label">Display name</label>
      <input className="input" maxLength={40} value={name} onChange={(e) => setName(e.target.value)} />
      <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm">
        <input type="checkbox" className="mt-1" checked={board} onChange={(e) => setBoard(e.target.checked)} />
        <span><span className="font-medium">Show me on the Virtual Invest leaderboard</span><span className="block text-xs muted">Only your display name and virtual return are shown. Off by default.</span></span>
      </label>
      <button className="btn-primary mt-4" disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>Save profile</button>
    </Card>
  )
}

function AccountCard() {
  const me = useMe()
  const user = me.data?.user
  const [mode, setMode] = useState<'register' | 'login'>('register')
  const [form, setForm] = useState({ username: '', password: '', display_name: '' })
  const qc = useQueryClient()
  const toast = useToast()
  const done = (msg: string) => { toast(msg); setForm({ username: '', password: '', display_name: '' }); qc.invalidateQueries() }
  const err = (e: unknown) => toast((e as Error).message, 'error')
  const submit = useMutation({
    mutationFn: () => api.post(mode === 'register' ? '/auth/register' : '/auth/login',
      { username: form.username.trim(), password: form.password, display_name: form.display_name.trim() || null }),
    onSuccess: () => done(mode === 'register' ? 'Account created - your guest data is kept' : 'Signed in'), onError: err,
  })
  const logout = useMutation({ mutationFn: () => api.post('/auth/logout', {}), onSuccess: () => done('Signed out'), onError: err })
  if (!user) return null
  const title = <span className="inline-flex items-center gap-1.5"><KeyRound className="h-4 w-4 text-brand-600" />Account</span>
  if (!user.is_guest) return (
    <Card title={title}>
      <p className="text-sm">Signed in as <b>{user.username}</b>. Your watchlists, portfolio, Virtual Invest account and documents are saved to this account.</p>
      <button className="btn-outline mt-4" disabled={logout.isPending} onClick={() => logout.mutate()}><LogOut className="h-4 w-4" />Sign out</button>
    </Card>
  )
  const valid = /^[A-Za-z0-9_.-]{3,30}$/.test(form.username) && form.password.length >= 8
  return (
    <Card title={title} subtitle="You are using a guest session tied to this browser. Create a free account to keep your data across browsers and devices.">
      <Segmented options={[{ id: 'register', label: 'Create account' }, { id: 'login', label: 'Sign in' }]} value={mode} onChange={setMode} />
      <form className="mt-4 space-y-3" onSubmit={(e) => { e.preventDefault(); if (valid) submit.mutate() }}>
        <div><label className="label">Username</label><input className="input" autoComplete="username" maxLength={30} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          {mode === 'register' && <p className="mt-1 text-xs muted">3–30 letters, numbers, dots, dashes or underscores.</p>}</div>
        <div><label className="label">Password</label><input className="input" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} maxLength={128} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          {mode === 'register' && <p className="mt-1 text-xs muted">At least 8 characters. Stored only as a salted scrypt hash.</p>}</div>
        {mode === 'register' && <div><label className="label">Display name (optional)</label><input className="input" maxLength={40} value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} /></div>}
        <button className="btn-primary" disabled={!valid || submit.isPending}><LogIn className="h-4 w-4" />{mode === 'register' ? 'Create account' : 'Sign in'}</button>
        {mode === 'login' && <p className="text-xs muted">Signing in switches to that account; data from this guest session stays with the guest session.</p>}
      </form>
    </Card>
  )
}

function AppearanceCard() {
  const [theme, setTheme] = useTheme()
  return (
    <Card title={<span className="inline-flex items-center gap-1.5"><Palette className="h-4 w-4 text-brand-600" />Appearance</span>}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm">Theme</span>
        <Segmented options={[{ id: 'light', label: <span className="inline-flex items-center gap-1"><Sun className="h-3.5 w-3.5" />Light</span> }, { id: 'dark', label: <span className="inline-flex items-center gap-1"><Moon className="h-3.5 w-3.5" />Dark</span> }]} value={theme} onChange={setTheme} />
      </div>
      <p className="mt-2 text-xs muted">Saved in this browser. Price colours: green for a rise, red for a fall, always alongside a +/− sign.</p>
    </Card>
  )
}

function AICard() {
  const q = useQuery({ queryKey: ['ai-settings'], queryFn: () => api.get<AISettings>('/assistant/settings') })
  const [s, setS] = useState<{ provider: AISettings['provider']; model: string; consent: boolean; api_key: string; ollama_host: string; ollama_model: string; effort: string } | null>(null)
  const qc = useQueryClient()
  const toast = useToast()
  useEffect(() => {
    if (q.data && !s) setS({ provider: q.data.provider, model: q.data.model || 'claude-haiku-5-5', consent: !!q.data.consent, api_key: '',
      ollama_host: q.data.ollama_host || 'http://localhost:11434', ollama_model: q.data.ollama_model || 'llama3.1', effort: q.data.effort || 'medium' })
  }, [q.data, s])
  const save = useMutation({
    mutationFn: () => api.put('/assistant/settings', { provider: s!.provider, model: s!.provider === 'anthropic' ? s!.model : null, consent: s!.consent,
      api_key: s!.api_key.trim() || null, ollama_host: s!.ollama_host, ollama_model: s!.ollama_model, effort: s!.effort }),
    onSuccess: () => { toast('AI settings saved'); setS((x) => x && { ...x, api_key: '' }); qc.invalidateQueries({ queryKey: ['ai-settings'] }) },
    onError: (e) => toast((e as Error).message, 'error'),
  })
  const title = <span className="inline-flex items-center gap-1.5"><Bot className="h-4 w-4 text-brand-600" />AI assistant engine</span>
  if (!q.data || !s) return <Card title={title}><Loading /></Card>
  const d = q.data
  const needsKey = s.provider === 'anthropic' && !d.key_configured && !s.api_key.trim()
  return (
    <Card title={title} subtitle="The free offline engine is the default. Paid engines are optional and need your explicit consent.">
      <div className="grid gap-2 sm:grid-cols-3">
        {([['offline', 'Offline analyst', 'Free · rule-based · no data leaves the app'], ['anthropic', 'Claude API', 'Paid per use · your own API key'], ['ollama', 'Ollama (local)', 'Free · runs a model on your computer']] as const).map(([id, label, sub]) => (
          <button key={id} onClick={() => setS({ ...s, provider: id })} className={cx('rounded-xl border p-3 text-left transition', s.provider === id ? 'border-brand-500 bg-brand-50 dark:bg-ink-700' : 'border-slate-200 hover:border-brand-300 dark:border-ink-600')}>
            <div className="text-sm font-semibold">{label}</div><div className="mt-0.5 text-xs muted">{sub}</div></button>))}
      </div>

      {s.provider === 'anthropic' && (
        <div className="mt-4 space-y-3">
          <Notice><b>Claude API billing is separate from Claude subscriptions.</b> A Claude Pro or Max plan, or access to Claude Code, does not include
            API usage. The Claude API is billed per token to an Anthropic API account (console.anthropic.com), and EquityPilot sends a request only
            after you add your own key and tick the consent box below.</Notice>
          <div className="text-xs muted">Status: {d.key_configured ? <span className="text-up">API key set for this browser session</span> : 'no API key set'}
            {' · '}{d.consent ? 'consent given' : 'consent not given'}{' · '}if a request fails, the free offline analyst answers instead and says why.</div>
          <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
            <thead><tr><th className="table-head px-2 py-2" /><th className="table-head px-2 py-2">Model</th><th className="table-head px-2 py-2 text-right">Input / output (USD per M tokens)</th><th className="table-head px-2 py-2 text-right">≈ per company question</th><th className="table-head px-2 py-2 text-right">≈ per document question</th></tr></thead>
            <tbody>{Object.entries(d.models).map(([id, m]) => (
              <tr key={id} className="cursor-pointer border-t border-slate-100 dark:border-ink-700" onClick={() => setS({ ...s, model: id })}>
                <td className="px-2 py-2"><input type="radio" checked={s.model === id} onChange={() => setS({ ...s, model: id })} aria-label={m.label} /></td>
                <td className="px-2 py-2">{m.label}</td><td className="num px-2 py-2 text-right">${m.in} / ${m.out}</td>
                <td className="num px-2 py-2 text-right">${d.estimates[id]?.company.toFixed(4)}</td><td className="num px-2 py-2 text-right">${d.estimates[id]?.document.toFixed(4)}</td>
              </tr>))}</tbody></table></div>
          <p className="text-xs muted">{d.pricing_note} Estimates assume ~6k input / 900 output tokens for a company question and ~30k / 1.5k for a document question. Each answer shows its own estimated cost.</p>
          <div><label className="label">Answer depth</label>
            <Segmented value={s.effort} onChange={(v) => setS({ ...s, effort: v })}
              options={[{ id: 'low', label: 'Quick' }, { id: 'medium', label: 'Balanced' }, { id: 'high', label: 'Thorough' }]} />
            <p className="mt-1 text-xs muted">How much the model reasons before answering. Quick is fastest and cheapest; Thorough takes longer and uses more output tokens.</p></div>
          <div><label className="label">Anthropic API key {d.key_configured && <span className="text-up">(a key is already set for this session)</span>}</label>
            <input className="input font-mono" type="password" autoComplete="off" placeholder="sk-ant-…" maxLength={300} value={s.api_key} onChange={(e) => setS({ ...s, api_key: e.target.value })} />
            <p className="mt-1 text-xs muted">Kept only in this browser's signed session cookie for the current session - never written to the database or logs. Get a key at console.anthropic.com (billing is on your Anthropic account).</p></div>
          <label className="flex cursor-pointer items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1" checked={s.consent} onChange={(e) => setS({ ...s, consent: e.target.checked })} />
            <span>I understand each question sends the company data and document excerpts in context to Anthropic and is billed to my API account at the rates above.</span>
          </label>
        </div>
      )}
      {s.provider === 'ollama' && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div><label className="label">Ollama host</label><input className="input" maxLength={200} value={s.ollama_host} onChange={(e) => setS({ ...s, ollama_host: e.target.value })} /></div>
          <div><label className="label">Model</label><input className="input" maxLength={80} value={s.ollama_model} onChange={(e) => setS({ ...s, ollama_model: e.target.value })} /></div>
          <p className="text-xs muted sm:col-span-2">Install Ollama from ollama.com and pull a model (e.g. <code>ollama pull llama3.1</code>). Local models are free but slower and less accurate; answers are still checked against the sources.</p>
        </div>
      )}
      <div className="mt-4 flex items-center gap-3">
        <button className="btn-primary" disabled={save.isPending || (s.provider === 'anthropic' && (!s.consent || needsKey))} onClick={() => save.mutate()}>Save AI settings</button>
        {s.provider === 'anthropic' && (!s.consent || needsKey) && <span className="text-xs muted">{needsKey ? 'Enter an API key' : 'Tick the consent box'} to enable Claude.</span>}
      </div>
    </Card>
  )
}

function DataCard() {
  const q = useQuery({ queryKey: ['data-sources'], queryFn: () => api.get<Sources>('/data/sources') })
  const toast = useToast()
  const exportData = async () => {
    try {
      const data = await api.get<unknown>('/me/export')
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const a = Object.assign(document.createElement('a'), { href: url, download: `equitypilot-my-data-${new Date().toISOString().slice(0, 10)}.json` })
      a.click(); URL.revokeObjectURL(url)
    } catch (e) { toast((e as Error).message, 'error') }
  }
  const title = <span className="inline-flex items-center gap-1.5"><Database className="h-4 w-4 text-brand-600" />Data sources</span>
  return (<>
    <Card title={title} subtitle={q.data ? `${q.data.companies_tracked} companies tracked · ${q.data.securities_listed.toLocaleString('en-IN')} listed securities searchable${q.data.offline ? ' · offline mode' : ''}` : undefined}>
      {!q.data ? <Loading /> : (<>
        <Notice tone="warn"><b>No real-time data.</b> {q.data.realtime_note}</Notice>
        <ul className="mt-4 divide-y divide-slate-100 dark:divide-ink-700">{q.data.sources.map((s) => (
          <li key={s.name} className="py-2.5 text-sm">
            <a className="inline-flex items-center gap-1 font-medium hover:underline" href={s.url} target="_blank" rel="noopener noreferrer">{s.name}<ExternalLink className="h-3 w-3" /></a>
            <div className="text-xs">{s.use}</div><div className="text-xs muted">{s.access}</div></li>))}</ul>
        <h4 className="mt-4 text-sm font-semibold">Feeds</h4>
        <ul className="mt-2 space-y-1 text-xs">{Object.entries(q.data.feeds).map(([k, f]) => (
          <li key={k} className="flex justify-between gap-3"><span>{f.source}</span><span className="shrink-0 muted">{f.last_refreshed ? `refreshed ${ist(f.last_refreshed)}` : 'not yet fetched'}</span></li>))}</ul>
        <p className="mt-3 text-xs muted">Prices: <DataBadge type="delayed" /> from Yahoo Finance via yfinance. Paid real-time options (a broker API on your own trading account, or a licensed vendor) are not connected; they would be added only with your approval.</p>
      </>)}
    </Card>
    <Card title="Your data" subtitle="Download everything stored for your profile as JSON: watchlists, alerts, holdings, Virtual Invest trades, saved screens and preferences.">
      <button className="btn-outline" onClick={exportData}><Download className="h-4 w-4" />Export my data</button>
      <p className="mt-3 text-xs muted">EquityPilot AI is an educational research tool and does not provide investment advice. Consult a SEBI-registered investment adviser before making investment decisions.</p>
    </Card>
  </>)
}
