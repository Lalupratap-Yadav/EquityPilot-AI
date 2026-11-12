import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ToastProvider } from './components/ui'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
})

// Establish the session cookie with one request before the app fires its parallel queries;
// otherwise a first-time visitor's simultaneous requests would each create a separate guest profile.
async function boot() {
  try {
    const me = await fetch('/api/me', { credentials: 'same-origin' })
    if (me.ok) queryClient.setQueryData(['me'], await me.json())
  } catch { /* offline or server down - pages show their own error states */ }
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastProvider><App /></ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  )
}
boot()
