import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '../../components/ui'
import { api } from '../../lib/api'
import type { LearnOverview, ProgressSummary } from './types'

export type ProgressEvent = { lesson: string; done: boolean } | { viewed: string } | { quiz: string; score: number; total: number }

/** Records a learning event and patches the cached overview with the returned progress (no refetch of the curriculum). */
export function useProgress(silent = false) {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (b: ProgressEvent) => api.post<ProgressSummary>('/learn/progress', b),
    onSuccess: (p) => qc.setQueryData<LearnOverview>(['learn'], (old) => (old ? { ...old, progress: p } : old)),
    onError: (e) => { if (!silent) toast((e as Error).message, 'error') },
  })
}
