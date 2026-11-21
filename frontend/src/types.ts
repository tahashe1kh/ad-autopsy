export interface Calculation {
  ctr_pct: number
  cpc: number | null
  click_to_lp_pct: number
  lp_to_atc_pct: number
  atc_to_purchase_pct: number
  cpa: number | null
  break_even_cpa: number
  fees_per_order: number
  revenue: number
  profit: number
  roas: number
  stop_loss_pct: number
  verdict: 'KILL' | 'FIX_LANDER' | 'SCALE' | 'NEED_MORE_DATA'
  reasoning: string[]
  formulas: Record<string, string>
  currency?: string
}

export interface TestInput {
  spend: number
  impressions: number
  clicks: number
  lp_views: number
  atc: number
  purchases: number
  price: number
  cogs: number
  fees_pct: number
  stop_loss: number
  currency: string
}

export interface SavedTest extends TestInput {
  id: number
  name: string
  notes: string
  created_at?: string
  calculation: Calculation
}

export interface CompetitorAd {
  id: number
  brand: string
  ad_id: string
  start_date: string | null
  format: string
  country: string
  active: boolean
  destination_url: string
  source: string
  problem_word: string
  notes: string
  days_running: number | null
  is_long_running: boolean
}

export interface BrandSummary {
  brand: string
  total_ads: number
  active_ads: number
  long_running_count: number
  oldest_start_date: string | null
  formats: Record<string, number>
  countries: Record<string, number>
}

export const NELUNA_TEST_1: TestInput = {
  spend: 123.66,
  impressions: 4114,
  clicks: 139,
  lp_views: 121,
  atc: 1,
  purchases: 0,
  price: 44.95,
  cogs: 11,
  fees_pct: 0,
  stop_loss: 300,
  currency: 'CAD',
}

export const FORMATS = [
  'first-person story',
  'confessional',
  'listicle',
  'testimonial',
  'doctor-led',
  'discount-led',
  'explanatory',
]
