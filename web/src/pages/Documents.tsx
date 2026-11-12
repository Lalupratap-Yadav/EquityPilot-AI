import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, ExternalLink, FileText, Search, Trash2, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { CompanyPicker } from '../components/CompanyPicker'
import { Card, DataBadge, EmptyState, Loading, Modal, Notice, PageHeader, useToast } from '../components/ui'
import { api } from '../lib/api'
import { baseSymbol, ist } from '../lib/format'
import { useInvalidate } from '../lib/hooks'

interface Doc { id: number; symbol: string | null; filename: string; doc_type: string; period: string; pages: number; source_url: string | null; uploaded_at: string }
interface Passage { page: number; text: string; score: number; chunk_id?: number }
interface UploadResp { id: number; pages: number; tables: number; scanned: boolean; truncated: boolean; warning: string | null }

const DOC_TYPES = ['Annual Report', 'Quarterly Results', 'Investor Presentation', 'Earnings Call Transcript', 'Credit Rating Report', 'Shareholding Pattern', 'Other filing']

export default function Documents() {
  const [symbol, setSymbol] = useState('')
  const [docType, setDocType] = useState(DOC_TYPES[0])
  const [period, setPeriod] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [searchDoc, setSearchDoc] = useState<Doc | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const toast = useToast()
  const inv = useInvalidate()
  const docs = useQuery({ queryKey: ['documents'], queryFn: () => api.get<Doc[]>('/documents') })

  const upload = useMutation({
    mutationFn: () => {
      const f = new FormData()
      f.append('file', file!)
      if (symbol) f.append('symbol', symbol)
      f.append('doc_type', docType)
      f.append('period', period)
      if (sourceUrl) f.append('source_url', sourceUrl)
      return api.upload<UploadResp>('/documents', f)
    },
    onSuccess: (r) => {
      toast(`Indexed ${r.pages} pages${r.tables ? ` and ${r.tables} tables` : ''}`)
      if (r.warning) toast(r.warning, 'error')
      setFile(null); if (fileRef.current) fileRef.current.value = ''
      inv('documents')
    },
    onError: (e) => toast((e as Error).message, 'error'),
  })
  const del = useMutation({ mutationFn: (id: number) => api.del(`/documents/${id}`), onSuccess: () => { toast('Document deleted'); inv('documents') } })
  const tooBig = !!file && file.size > 50 * 1024 * 1024

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Research" title="Documents"
        subtitle="Upload annual reports, results, presentations and call transcripts as PDFs. EquityPilot extracts the text page by page so the AI Assistant can answer questions with page citations. Your documents are visible only to you." />

      <Card title={<span className="inline-flex items-center gap-1.5"><Upload className="h-4 w-4 text-brand-600" />Upload a PDF</span>}
        subtitle="Download filings yourself from the company website, NSE or BSE, then upload them here. EquityPilot does not download them automatically.">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div><label className="label">PDF file (max 50 MB)</label>
            <input ref={fileRef} type="file" accept="application/pdf,.pdf" className="input file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-brand-700 dark:file:bg-ink-700 dark:file:text-brand-200"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></div>
          <div><label className="label">Company (optional)</label><CompanyPicker value={symbol} trackedOnly onChange={setSymbol} />
            {symbol && <div className="mt-1 flex justify-between text-xs muted"><span>{baseSymbol(symbol)}</span><button onClick={() => setSymbol('')}>Clear</button></div>}</div>
          <div><label className="label">Document type</label>
            <select className="input" value={docType} onChange={(e) => setDocType(e.target.value)}>{DOC_TYPES.map((t) => <option key={t}>{t}</option>)}</select></div>
          <div><label className="label">Period</label><input className="input" placeholder="e.g. FY25 or Q2 FY26" maxLength={30} value={period} onChange={(e) => setPeriod(e.target.value)} /></div>
          <div className="md:col-span-2 xl:col-span-3"><label className="label">Source URL (where you downloaded it)</label><input className="input" placeholder="https://…" maxLength={500} value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} /></div>
          <div className="flex items-end"><button className="btn-primary w-full" disabled={!file || tooBig || upload.isPending} onClick={() => upload.mutate()}>
            <Upload className="h-4 w-4" />{upload.isPending ? 'Extracting text…' : 'Upload & index'}</button></div>
        </div>
        {tooBig && <Notice tone="warn" className="mt-3">This file is larger than 50 MB. Try the company's “standalone” or section-wise PDF.</Notice>}
        <p className="mt-3 text-xs muted">Scanned (image-only) PDFs have no extractable text, and OCR is not included. A source URL lets reports and answers link back to the original filing.</p>
      </Card>

      <Card title="Your documents" pad={false}>
        {docs.isLoading ? <Loading /> : (docs.data ?? []).length === 0 ? (
          <EmptyState icon={<FileText className="h-6 w-6" />} title="No documents yet" body="Upload a PDF above, then ask the AI Assistant about it." />
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-ink-700">{docs.data!.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
              <FileText className="h-5 w-5 shrink-0 text-brand-600" />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{d.filename}</div>
                <div className="text-xs muted">
                  {d.symbol ? <Link className="hover:underline" to={`/company/${encodeURIComponent(d.symbol)}`}>{baseSymbol(d.symbol)}</Link> : 'No company'} · {d.doc_type}{d.period ? ` · ${d.period}` : ''} · {d.pages} pages · uploaded {ist(d.uploaded_at)}
                </div>
              </div>
              <DataBadge type="official_upload" />
              <div className="flex gap-1">
                {d.source_url && <a className="btn-ghost p-2" href={d.source_url} target="_blank" rel="noopener noreferrer" aria-label="Open source"><ExternalLink className="h-4 w-4" /></a>}
                <button className="btn-ghost p-2" onClick={() => setSearchDoc(d)} aria-label="Search inside"><Search className="h-4 w-4" /></button>
                <Link className="btn-ghost p-2" to={`/assistant${d.symbol ? `?symbol=${encodeURIComponent(d.symbol)}` : ''}`} aria-label="Ask the assistant"><Bot className="h-4 w-4" /></Link>
                <button className="btn-ghost p-2" onClick={() => confirm(`Delete "${d.filename}" and its index?`) && del.mutate(d.id)} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
              </div>
            </li>))}</ul>
        )}
      </Card>

      <Modal open={!!searchDoc} onClose={() => setSearchDoc(null)} title={`Search · ${searchDoc?.filename ?? ''}`} wide>
        {searchDoc && <DocSearch doc={searchDoc} />}
      </Modal>
    </div>
  )
}

function DocSearch({ doc }: { doc: Doc }) {
  const [q, setQ] = useState('')
  const [term, setTerm] = useState('')
  const res = useQuery({ queryKey: ['doc-search', doc.id, term], enabled: term.length > 1,
    queryFn: () => api.get<{ passages: Passage[] }>(`/documents/${doc.id}/search?q=${encodeURIComponent(term)}`) })
  return (
    <div className="space-y-3">
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); setTerm(q.trim()) }}>
        <input className="input flex-1" autoFocus placeholder="e.g. capital expenditure, order book, contingent liabilities" maxLength={200} value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-primary" disabled={q.trim().length < 2}><Search className="h-4 w-4" />Search</button>
      </form>
      {res.isFetching ? <Loading /> : term && (res.data?.passages ?? []).length === 0 ? <p className="text-sm muted">No matching passages.</p> : (
        <ul className="max-h-[60vh] space-y-2 overflow-y-auto">{(res.data?.passages ?? []).map((p, i) => (
          <li key={i} className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-ink-800">
            <div className="mb-1 text-xs font-semibold text-brand-600 dark:text-brand-300">Page {p.page}</div>
            <p className="whitespace-pre-line leading-relaxed">{p.text.slice(0, 700)}{p.text.length > 700 ? '…' : ''}</p>
          </li>))}</ul>
      )}
    </div>
  )
}
