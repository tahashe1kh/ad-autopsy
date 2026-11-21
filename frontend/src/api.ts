import type { BrandSummary, Calculation, CompetitorAd, SavedTest, TestInput } from './types'

const API = (import.meta as unknown as { env: Record<string, string | undefined> }).env.VITE_API_URL || 'http://localhost:8000'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => req<{ status: string; tests: number; ads: number }>('/api/health'),
  calculate: (input: TestInput) =>
    req<Calculation>('/api/calculate', { method: 'POST', body: JSON.stringify(input) }),
  listTests: () => req<SavedTest[]>('/api/tests'),
  createTest: (name: string, notes: string, input: TestInput) =>
    req<SavedTest>('/api/tests', { method: 'POST', body: JSON.stringify({ name, notes, ...input }) }),
  deleteTest: (id: number) => req<{ deleted: number }>(`/api/tests/${id}`, { method: 'DELETE' }),
  importCsvText: (csvText: string, price: number, cogs: number) =>
    req<{ created: number; warnings: string[]; tests: SavedTest[] }>('/api/tests/import-csv', {
      method: 'POST',
      body: JSON.stringify({ csv_text: csvText, price, cogs }),
    }),
  importCsvFile: async (file: File, price: number, cogs: number) => {
    const form = new FormData()
    form.append('file', file)
    form.append('price', String(price))
    form.append('cogs', String(cogs))
    const res = await fetch(`${API}/api/tests/import-csv`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<{ created: number; warnings: string[]; tests: SavedTest[] }>
  },
  listAds: (params: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString()
    return req<CompetitorAd[]>(`/api/ads${qs ? `?${qs}` : ''}`)
  },
  createAd: (ad: Record<string, unknown>) =>
    req<CompetitorAd>('/api/ads', { method: 'POST', body: JSON.stringify(ad) }),
  deleteAd: (id: number) => req<{ deleted: number }>(`/api/ads/${id}`, { method: 'DELETE' }),
  summary: () => req<BrandSummary[]>('/api/competitors/summary'),
}
