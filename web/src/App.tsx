import { lazy, Suspense } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { EmptyState, Loading } from './components/ui'
import Home from './pages/Home'

const pages = {
  Explore: lazy(() => import('./pages/Explore')),
  Industries: lazy(() => import('./pages/Industries')),
  Industry: lazy(() => import('./pages/Industry')),
  Markets: lazy(() => import('./pages/Markets')),
  Company: lazy(() => import('./pages/Company')),
  Research: lazy(() => import('./pages/Research')),
  Valuation: lazy(() => import('./pages/Valuation')),
  Screener: lazy(() => import('./pages/Screener')),
  Compare: lazy(() => import('./pages/Compare')),
  News: lazy(() => import('./pages/News')),
  Earnings: lazy(() => import('./pages/Earnings')),
  CorporateActions: lazy(() => import('./pages/CorporateActions')),
  DataQuality: lazy(() => import('./pages/DataQuality')),
  Assistant: lazy(() => import('./pages/Assistant')),
  Reports: lazy(() => import('./pages/Reports')),
  Watchlists: lazy(() => import('./pages/Watchlists')),
  Portfolio: lazy(() => import('./pages/Portfolio')),
  Invest: lazy(() => import('./pages/Invest')),
  Documents: lazy(() => import('./pages/Documents')),
  Learn: lazy(() => import('./pages/Learn')),
  Guide: lazy(() => import('./pages/Guide')),
  Settings: lazy(() => import('./pages/Settings')),
}

function NotFound() {
  return <EmptyState title="Page not found" body="The page you're looking for doesn't exist." action={<Link to="/" className="btn-primary">Go home</Link>} />
}

export default function App() {
  const P = pages
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="explore" element={<P.Explore />} />
          <Route path="industries" element={<P.Industries />} />
          <Route path="industries/:id" element={<P.Industry />} />
          <Route path="markets" element={<P.Markets />} />
          <Route path="company/:symbol" element={<P.Company />} />
          <Route path="research" element={<P.Research />} />
          <Route path="valuation" element={<P.Valuation />} />
          <Route path="valuation/:symbol" element={<P.Valuation />} />
          <Route path="screener" element={<P.Screener />} />
          <Route path="compare" element={<P.Compare />} />
          <Route path="news" element={<P.News />} />
          <Route path="earnings" element={<P.Earnings />} />
          <Route path="corporate-actions" element={<P.CorporateActions />} />
          <Route path="data-quality" element={<P.DataQuality />} />
          <Route path="assistant" element={<P.Assistant />} />
          <Route path="reports" element={<P.Reports />} />
          <Route path="watchlists" element={<P.Watchlists />} />
          <Route path="portfolio" element={<P.Portfolio />} />
          <Route path="invest" element={<P.Invest />} />
          <Route path="documents" element={<P.Documents />} />
          <Route path="learn" element={<P.Learn />} />
          <Route path="guide" element={<P.Guide />} />
          <Route path="settings" element={<P.Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
