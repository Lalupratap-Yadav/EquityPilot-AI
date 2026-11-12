import { Fragment, type ReactNode } from 'react'

/** Small, safe Markdown renderer (no raw HTML): headings, paragraphs, bullet & numbered lists,
 *  pipe tables, **bold**, *italic* and _italic_. Used for learning content and assistant answers. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|_[^_]+_)/g).map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>
    if ((p.startsWith('*') && p.endsWith('*') && p.length > 2) || (p.startsWith('_') && p.endsWith('_') && p.length > 2)) return <em key={i}>{p.slice(1, -1)}</em>
    return <Fragment key={i}>{p}</Fragment>
  })
}

export function Markdown({ text, className }: { text: string; className?: string }) {
  const lines = text.trim().split('\n')
  const out: ReactNode[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (/^#{1,4}\s/.test(line)) {
      out.push(<h4 key={i} className="mt-2 font-semibold">{inline(line.replace(/^#+\s/, ''))}</h4>); i++; continue
    }
    if (line.trim().startsWith('|')) {
      const rows: string[][] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        const cells = lines[i].trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
        if (!cells.every((c) => /^:?-{2,}:?$/.test(c))) rows.push(cells)
        i++
      }
      out.push(
        <div key={`t${i}`} className="overflow-x-auto"><table className="w-full min-w-max text-sm">
          <thead><tr>{rows[0].map((c, k) => <th key={k} className="table-head px-3 py-2">{inline(c)}</th>)}</tr></thead>
          <tbody>{rows.slice(1).map((r, k) => <tr key={k} className="border-t border-slate-100 dark:border-ink-700">{r.map((c, j) => <td key={j} className="px-3 py-2 align-top">{inline(c)}</td>)}</tr>)}</tbody>
        </table></div>)
      continue
    }
    if (/^\s*([-*]|\d+\.)\s/.test(line)) {
      const ordered = /^\s*\d+\.\s/.test(line)
      const items: ReactNode[] = []
      while (i < lines.length && (/^\s*([-*]|\d+\.)\s/.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
        if (/^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s/.test(lines[i])) {
          items.push(<li key={i} className="list-none text-slate-500 dark:text-slate-400">{inline(lines[i].trim())}</li>)
        } else {
          items.push(<li key={i}>{inline(lines[i].replace(/^\s*([-*]|\d+\.)\s/, ''))}</li>)
        }
        i++
      }
      out.push(ordered ? <ol key={`o${i}`} className="list-decimal space-y-1 pl-5">{items}</ol> : <ul key={`u${i}`} className="list-disc space-y-1 pl-5">{items}</ul>)
      continue
    }
    const para: string[] = []
    while (i < lines.length && lines[i].trim() && !/^\s*([-*]|\d+\.)\s/.test(lines[i]) && !lines[i].trim().startsWith('|') && !/^#{1,4}\s/.test(lines[i])) { para.push(lines[i]); i++ }
    out.push(<p key={`p${i}`}>{inline(para.join(' '))}</p>)
  }
  return <div className={className ?? 'space-y-3 text-sm leading-relaxed'}>{out}</div>
}
