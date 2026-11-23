// Chart colours shared by every chart. Kept free of chart-library imports so pages that only need a colour or a
// sparkline (Home, Markets, Industries, the price chart) do not download the recharts bundle.
import { useTheme } from '../lib/hooks'

// Validated categorical palette (fixed order); dark-mode steps chosen for the dark surface.
export const SERIES_LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
export const SERIES_DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
export const UP = '#12a150'
export const DOWN = '#dc3545'

export function useSeriesColors() {
  const [theme] = useTheme()
  return theme === 'dark' ? SERIES_DARK : SERIES_LIGHT
}

export function useAxisColors() {
  const [theme] = useTheme()
  return theme === 'dark'
    ? { grid: '#1e2a45', text: '#8a95ad', tooltipBg: '#0f172b', border: '#2c3a5a' }
    : { grid: '#eef1f5', text: '#8a8f98', tooltipBg: '#ffffff', border: '#e3e8f0' }
}
