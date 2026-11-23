import { Fragment, type ReactNode } from 'react'

/** Small, safe Markdown renderer (no raw HTML): headings, paragraphs, bullet & numbered lists, pipe tables, > notes,
 *  **bold**, *italic* and _italic_. Used for learning content and assistant answers. Source tags such as [T2] become
 *  chips; with `onCite` they are buttons that open that source. */
type Cite = ((id: string) => void) | undefined

const CHIP = 'rounded bg-brand-50 px-1 text-[10px] font-semibold not-italic text-brand-700 dark:bg-brand-500/15 dark:text-brand-200'

function inline(text: string, onCite?: Cite): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|_[^_\s][^_]*_|\[[STD]\d+(?:\s*[,;]\s*[STD]\d+)*\])/g).map((p, i) => {
    if (/^\[[STD]\d+(?:\s*[,;]\s*[STD]\d+)*\]$/.test(p)) {
      return <sup key={i} className="ml-0.5 inline-flex gap-0.5 align-super">{p.slice(1, -1).split(/\s*[,;]\s*/).map((id) => (onCite
        ? <button key={id} type="button" onClick={() => onCite(id)} title={`Show source ${id}`} className={`${CHIP} hover:bg-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 dark:hover:bg-brand-500/30`}>{id}</button>
        : <span key={id} title={`Source ${id} - listed under "Sources used"`} className={CHIP}>{id}</span>))}</sup>
    }
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{inline(p.slice(2, -2), onCite)}</strong>
    if ((p.startsWith('*') && p.endsWith('*') && p.length > 2) || (p.startsWith('_') && p.endsWith('_') && p.length > 2)) return <em key={i}>{p.slice(1, -1)}</em>
    return <Fragment key={i}>{p}</Fragment>
  })
}

export function Markdown({ text, className, onCite }: { text: string; className?: string; onCite?: (id: string) => void }) {
  const lines = text.trim().split('\n')
  const out: ReactNode[] = []
  let i = 0
  const inl = (t: string) => inline(t, onCite)
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (/^\s*>\s?/.test(line)) {
      const notes: string[] = []
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) { notes.push(lines[i].replace(/^\s*>\s?/, '')); i++ }
      out.push(<div key={`n${i}`} className="rounded-lg border-l-2 border-saffron-500 bg-amber-50/70 px-3 py-2 text-[13px] dark:bg-saffron-500/10">{notes.map((n, k) => <p key={k}>{inl(n)}</p>)}</div>)
      continue
    }
    if (/^#{1,4}\s/.test(line)) {
      out.push(<h4 key={i} className="mt-3 text-[15px] font-semibold">{inl(line.replace(/^#+\s/, ''))}</h4>); i++; continue
    }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(line)) { out.push(<hr key={i} className="border-slate-200 dark:border-ink-700" />); i++; continue }
    if (line.trim().startsWith('|')) {
      const rows: string[][] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        const cells = lines[i].trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
        if (!cells.every((c) => /^:?-{2,}:?$/.test(c))) rows.push(cells)
        i++
      }
      out.push(
        <div key={`t${i}`} className="overflow-x-auto"><table className="w-full min-w-max text-sm">
          <thead><tr>{rows[0].map((c, k) => <th key={k} className="table-head px-3 py-2">{inl(c)}</th>)}</tr></thead>
          <tbody>{rows.slice(1).map((r, k) => <tr key={k} className="border-t border-slate-100 dark:border-ink-700">{r.map((c, j) => <td key={j} className="px-3 py-2 align-top">{inl(c)}</td>)}</tr>)}</tbody>
        </table></div>)
      continue
    }
    if (/^\s*([-*]|\d+\.)\s/.test(line)) {
      const ordered = /^\s*\d+\.\s/.test(line)
      const items: ReactNode[] = []
      while (i < lines.length && (/^\s*([-*]|\d+\.)\s/.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
        if (/^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s/.test(lines[i])) {
          items.push(<li key={i} className="list-none text-slate-500 dark:text-slate-400">{inl(lines[i].trim())}</li>)
        } else {
          items.push(<li key={i}>{inl(lines[i].replace(/^\s*([-*]|\d+\.)\s/, ''))}</li>)
        }
        i++
      }
      out.push(ordered ? <ol key={`o${i}`} className="list-decimal space-y-1 pl-5">{items}</ol> : <ul key={`u${i}`} className="list-disc space-y-1 pl-5">{items}</ul>)
      continue
    }
    const para: string[] = []
    while (i < lines.length && lines[i].trim() && !/^\s*([-*]|\d+\.)\s/.test(lines[i]) && !lines[i].trim().startsWith('|') && !/^#{1,4}\s/.test(lines[i])) { para.push(lines[i]); i++ }
    out.push(<p key={`p${i}`}>{inl(para.join(' '))}</p>)
  }
  return <div className={className ?? 'space-y-3 text-sm leading-relaxed'}>{out}</div>
}
