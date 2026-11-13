import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Component, type ErrorInfo, type ReactNode } from 'react'

/** After a new build is deployed, an open tab may ask for page code that no longer exists. Reload once to fetch the
 *  new version instead of showing an error. */
function isStaleChunk(err: unknown): boolean {
  const msg = String((err as Error)?.message ?? err)
  return /dynamically imported module|Importing a module script failed|Failed to fetch dynamically|ChunkLoadError|error loading dynamically/i.test(msg)
}

interface Props { children: ReactNode; scope?: 'page' | 'app' }
interface State { error: Error | null }

/** Keeps one broken widget or page from blanking the whole site. A page-level boundary resets when the route
 *  changes (it is keyed by the path in Layout), so the rest of the app keeps working. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (isStaleChunk(error)) {
      try {
        if (!sessionStorage.getItem('ep-chunk-reload')) {
          sessionStorage.setItem('ep-chunk-reload', '1')
          window.location.reload()
          return
        }
      } catch { /* storage unavailable: fall through to the message */ }
    }
    console.error('EquityPilot UI error:', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children
    const stale = isStaleChunk(error)
    return (
      <div role="alert" className={this.props.scope === 'app' ? 'flex min-h-screen items-center justify-center p-6' : 'py-10'}>
        <div className="card mx-auto max-w-lg p-6 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-saffron-500" />
          <h2 className="mt-3 text-lg font-semibold">{stale ? 'A newer version of EquityPilot is available' : 'This part of the page could not be shown'}</h2>
          <p className="mt-1 text-sm muted">{stale ? 'Reload to continue with the latest version.'
            : 'Something unexpected happened while displaying this page. Your data is safe. Try again, or go back to the home page.'}</p>
          {!stale && <p className="mt-3 break-words rounded-lg bg-slate-50 p-2 text-left font-mono text-[11px] text-slate-500 dark:bg-ink-800">{error.message}</p>}
          <div className="mt-4 flex justify-center gap-2">
            <button className="btn-primary" onClick={() => { try { sessionStorage.removeItem('ep-chunk-reload') } catch { /* ignore */ } window.location.reload() }}>
              <RefreshCw className="h-4 w-4" />Reload</button>
            {!stale && <button className="btn-outline" onClick={() => this.setState({ error: null })}>Try again</button>}
            {!stale && <a className="btn-ghost" href="/">Home</a>}
          </div>
        </div>
      </div>
    )
  }
}
