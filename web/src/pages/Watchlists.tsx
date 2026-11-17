import { useMutation, useQuery } from '@tanstack/react-query'
import { Bell, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertButton, CompanyAvatar } from '../components/common'
import { CompanyPicker } from '../components/CompanyPicker'
import { Card, ChangePill, cx, DataBadge, EmptyState, Loading, Modal, PageHeader, useToast } from '../components/ui'
import { api, type Quote } from '../lib/api'
import { baseSymbol, inr, ist } from '../lib/format'
import { useInvalidate, useQuoteStream } from '../lib/hooks'

interface Item { symbol: string; name: string; note: string | null; price: number | null; change_pct: number | null; status: Quote['status']; time: string | null }
interface WL { id: number; name: string; items: Item[] }
interface Alert { id: number; symbol: string; direction: string; price: number; active: boolean; created_at: string; triggered_at: string | null; triggered_price: number | null }

export default function Watchlists() {
  const q = useQuery({ queryKey: ['watchlists'], queryFn: () => api.get<WL[]>('/watchlists') })
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => api.get<Alert[]>('/alerts') })
  const [active, setActive] = useState<number | null>(null)
  const [edit, setEdit] = useState<{ id?: number; name: string } | null>(null)
  const [note, setNote] = useState<{ symbol: string; note: string } | null>(null)
  const inv = useInvalidate()
  const toast = useToast()
  const lists = q.data ?? []
  const wl = lists.find((w) => w.id === active) ?? lists[0]
  const stream = useQuoteStream((wl?.items ?? []).map((i) => i.symbol))
  const err = (e: unknown) => toast((e as Error).message, 'error')
  const saveList = useMutation({ mutationFn: () => (edit?.id ? api.patch(`/watchlists/${edit.id}`, { name: edit.name }) : api.post<{ id: number }>('/watchlists', { name: edit!.name })),
    onSuccess: (r) => { inv('watchlists'); setEdit(null); if (r && (r as { id?: number }).id) setActive((r as { id: number }).id) }, onError: err })
  const delList = useMutation({ mutationFn: (id: number) => api.del(`/watchlists/${id}`), onSuccess: () => { inv('watchlists'); setActive(null) }, onError: err })
  const addItem = useMutation({ mutationFn: (symbol: string) => api.post(`/watchlists/${wl!.id}/items`, { symbol }), onSuccess: () => inv('watchlists'), onError: err })
  const delItem = useMutation({ mutationFn: (symbol: string) => api.del(`/watchlists/${wl!.id}/items/${encodeURIComponent(symbol)}`), onSuccess: () => inv('watchlists') })
  const saveNote = useMutation({ mutationFn: () => api.patch(`/watchlists/${wl!.id}/items/${encodeURIComponent(note!.symbol)}`, { symbol: note!.symbol, note: note!.note }), onSuccess: () => { inv('watchlists'); setNote(null) } })
  const delAlert = useMutation({ mutationFn: (id: number) => api.del(`/alerts/${id}`), onSuccess: () => inv('alerts') })

  if (q.isLoading) return <Loading />
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="My space" title="Watchlists" subtitle="Track companies across multiple lists, keep notes on why you're watching, and set price alerts (checked against the latest delayed price)."
        actions={<button className="btn-primary" onClick={() => setEdit({ name: '' })}><Plus className="h-4 w-4" />New watchlist</button>} />
      <div className="flex flex-wrap gap-2">
        {lists.map((w) => (
          <button key={w.id} onClick={() => setActive(w.id)} className={cx('chip px-4 py-2 text-sm', wl?.id === w.id && 'chip-active')}>{w.name} <span className="muted">{w.items.length}</span></button>))}
      </div>
      {wl && (
        <Card title={wl.name} subtitle={stream.updatedAt ? `Prices auto-update · last update ${new Date(stream.updatedAt).toLocaleTimeString('en-IN')}` : undefined}
          action={<div className="flex gap-1"><button className="btn-ghost p-2" onClick={() => setEdit({ id: wl.id, name: wl.name })} aria-label="Rename"><Pencil className="h-4 w-4" /></button>
            <button className="btn-ghost p-2" onClick={() => confirm(`Delete "${wl.name}"?`) && delList.mutate(wl.id)} aria-label="Delete watchlist"><Trash2 className="h-4 w-4" /></button></div>}>
          <CompanyPicker className="mb-4 max-w-md" placeholder="Add a company to this watchlist…" trackedOnly onChange={(s) => addItem.mutate(s)} />
          {wl.items.length === 0 ? <EmptyState title="No companies yet" body="Search above to add companies. Only tracked companies can be added - open an untracked company's page first to fetch its data." /> : (
            <div className="overflow-x-auto"><table className="w-full min-w-max text-sm">
              <thead><tr><th className="table-head px-3 py-2.5">Company</th><th className="table-head px-3 py-2.5 text-right">Price</th><th className="table-head px-3 py-2.5 text-right">Day change</th><th className="table-head px-3 py-2.5">Data</th><th className="table-head px-3 py-2.5">Note</th><th className="table-head px-3 py-2.5" /></tr></thead>
              <tbody>{wl.items.map((i) => {
                const lq = stream.quotes[i.symbol]
                return (
                  <tr key={i.symbol} className="border-t border-slate-100 dark:border-ink-700">
                    <td className="px-3 py-2.5"><Link to={`/company/${encodeURIComponent(i.symbol)}`} className="flex items-center gap-2.5 hover:underline"><CompanyAvatar symbol={i.symbol} size="sm" /><span><span className="block font-medium">{i.name}</span><span className="text-[11px] muted">{baseSymbol(i.symbol)}</span></span></Link></td>
                    <td className="num px-3 py-2.5 text-right font-semibold">{inr(lq?.price ?? i.price)}</td>
                    <td className="px-3 py-2.5 text-right"><ChangePill value={lq?.change_pct ?? i.change_pct} /></td>
                    <td className="px-3 py-2.5"><DataBadge type={lq?.status ?? i.status} /> <span className="text-[11px] muted">{ist(lq?.time ?? i.time)}</span></td>
                    <td className="max-w-xs px-3 py-2.5"><button className="truncate text-left text-xs muted hover:text-brand-600" onClick={() => setNote({ symbol: i.symbol, note: i.note ?? '' })}>{i.note || '+ Add note'}</button></td>
                    <td className="px-3 py-2.5 text-right"><span className="inline-flex gap-1"><AlertButton symbol={i.symbol} price={lq?.price ?? i.price} />
                      <button className="btn-ghost p-2" onClick={() => delItem.mutate(i.symbol)} aria-label="Remove"><Trash2 className="h-4 w-4" /></button></span></td>
                  </tr>)
              })}</tbody></table></div>
          )}
        </Card>
      )}
      <Card title={<span className="inline-flex items-center gap-1.5"><Bell className="h-4 w-4 text-brand-600" />Price alerts</span>} subtitle="Alerts are checked against the latest available (delayed) price when the app is open; triggered alerts appear in notifications.">
        {(alerts.data ?? []).length === 0 ? <p className="text-sm muted">No alerts. Use the Alert button on a company page or in a watchlist row.</p> : (
          <ul className="divide-y divide-slate-100 dark:divide-ink-700">{alerts.data!.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <span><Link className="font-semibold hover:underline" to={`/company/${encodeURIComponent(a.symbol)}`}>{baseSymbol(a.symbol)}</Link> {a.direction} {inr(a.price)}</span>
              <span className={cx('text-xs', a.active ? 'text-brand-600' : 'text-up')}>{a.active ? 'Active' : `Triggered ${ist(a.triggered_at)} at ${inr(a.triggered_price)}`}</span>
              <button className="btn-ghost p-1.5" onClick={() => delAlert.mutate(a.id)} aria-label="Delete alert"><Trash2 className="h-4 w-4" /></button></li>))}</ul>
        )}
      </Card>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? 'Rename watchlist' : 'New watchlist'}>
        <input className="input" autoFocus maxLength={40} placeholder="e.g. Banking ideas" value={edit?.name ?? ''} onChange={(e) => setEdit({ ...edit!, name: e.target.value })} />
        <button className="btn-primary mt-4 w-full" disabled={!edit?.name.trim()} onClick={() => saveList.mutate()}>Save</button>
      </Modal>
      <Modal open={!!note} onClose={() => setNote(null)} title={`Note · ${note ? baseSymbol(note.symbol) : ''}`}>
        <textarea className="input min-h-[120px]" maxLength={1000} placeholder="Private note - only you can see it" value={note?.note ?? ''} onChange={(e) => setNote({ ...note!, note: e.target.value })} />
        <button className="btn-primary mt-4 w-full" onClick={() => saveNote.mutate()}>Save note</button>
      </Modal>
    </div>
  )
}
