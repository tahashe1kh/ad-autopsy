import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { FORMATS, NELUNA_TEST_1 } from './types'
import type { BrandSummary, Calculation, CompetitorAd, SavedTest, TestInput } from './types'

const VERDICT_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  KILL: { label: 'KILL', color: '#991b1b', bg: '#fef2f2', border: '#fecaca' },
  FIX_LANDER: { label: 'FIX LANDER', color: '#92400e', bg: '#fffbeb', border: '#fde68a' },
  SCALE: { label: 'SCALE', color: '#166534', bg: '#f0fdf4', border: '#bbf7d0' },
  NEED_MORE_DATA: { label: 'NEED MORE DATA', color: '#404040', bg: '#f5f5f4', border: '#e7e5e4' },
}

const NUM_FIELDS: { key: keyof TestInput; label: string; step: string }[] = [
  { key: 'spend', label: 'Spend ($)', step: '0.01' },
  { key: 'impressions', label: 'Impressions', step: '1' },
  { key: 'clicks', label: 'Link clicks', step: '1' },
  { key: 'lp_views', label: 'Landing page views', step: '1' },
  { key: 'atc', label: 'Add to carts', step: '1' },
  { key: 'purchases', label: 'Purchases', step: '1' },
  { key: 'price', label: 'Price ($)', step: '0.01' },
  { key: 'cogs', label: 'COGS per unit ($)', step: '0.01' },
  { key: 'fees_pct', label: 'Fees (% of price)', step: '0.1' },
  { key: 'stop_loss', label: 'Stop loss ($)', step: '1' },
]

function money(n: number | null | undefined, currency = '') {
  if (n === null || n === undefined) return '—'
  return `${currency ? currency + ' ' : ''}$${n.toFixed(2)}`
}

function Funnel({ input }: { input: TestInput }) {
  const stages = [
    { label: 'Impressions', value: input.impressions, pct: 100 },
    { label: 'Clicks', value: input.clicks, pct: input.impressions ? (input.clicks / input.impressions) * 100 : 0 },
    { label: 'LP views', value: input.lp_views, pct: input.clicks ? (input.lp_views / input.clicks) * 100 : 0 },
    { label: 'Add to carts', value: input.atc, pct: input.lp_views ? (input.atc / input.lp_views) * 100 : 0 },
    { label: 'Purchases', value: input.purchases, pct: input.atc ? (input.purchases / input.atc) * 100 : 0 },
  ]
  const max = Math.max(input.impressions, 1)
  return (
    <div className="funnel">
      {stages.map((s, i) => (
        <div key={s.label} className="funnel-row">
          <div className="funnel-label">{s.label}</div>
          <div className="funnel-bar-wrap">
            <div
              className="funnel-bar"
              style={{ width: `${Math.max((s.value / max) * 100, s.value > 0 ? 2 : 0)}%` }}
            />
          </div>
          <div className="funnel-value">{s.value.toLocaleString()}</div>
          <div className="funnel-pct">{i === 0 ? '100% of stage' : `${s.pct.toFixed(2)}% carry over`}</div>
        </div>
      ))}
    </div>
  )
}

function KillSwitch() {
  const [input, setInput] = useState<TestInput>(NELUNA_TEST_1)
  const [testName, setTestName] = useState('Neluna Test 1 — Nov 14-15')
  const [calc, setCalc] = useState<Calculation | null>(null)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState<SavedTest[]>([])
  const [savedMsg, setSavedMsg] = useState('')
  const [csvText, setCsvText] = useState(
    'ad_name,spend,impressions,clicks,lp_views,atc,purchases\nTest Ad A,100,10000,300,260,13,4',
  )
  const [importMsg, setImportMsg] = useState('')

  const loadSaved = useCallback(async () => {
    try {
      setSaved(await api.listTests())
    } catch {
      setError('Backend not reachable at http://localhost:8000 — start it first (see README).')
    }
  }, [])

  useEffect(() => {
    loadSaved()
  }, [loadSaved])

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .calculate(input)
        .then(setCalc)
        .catch(() => setError('Could not calculate — is the backend running?'))
    }, 250)
    return () => clearTimeout(t)
  }, [input])

  const setNum = (key: keyof TestInput, v: string) =>
    setInput((prev) => ({ ...prev, [key]: v === '' ? 0 : Number(v) }))

  const loadTest = (t: SavedTest) => {
    setInput({
      spend: t.spend, impressions: t.impressions, clicks: t.clicks,
      lp_views: t.lp_views, atc: t.atc, purchases: t.purchases,
      price: t.price, cogs: t.cogs, fees_pct: t.fees_pct,
      stop_loss: t.stop_loss, currency: t.currency,
    })
    setTestName(t.name)
  }

  const saveCurrent = async () => {
    try {
      await api.createTest(testName || 'Untitled test', '', input)
      setSavedMsg('Saved.')
      loadSaved()
    } catch (e) {
      setSavedMsg(`Save failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  const doImport = async () => {
    setImportMsg('')
    try {
      const r = await api.importCsvText(csvText, input.price, input.cogs)
      setImportMsg(`Imported ${r.created} test(s).${r.warnings.length ? ' Warnings: ' + r.warnings.join(' ') : ''}`)
      loadSaved()
    } catch (e) {
      setImportMsg(`Import failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  const onFile = async (f: File | undefined) => {
    if (!f) return
    try {
      const r = await api.importCsvFile(f, input.price, input.cogs)
      setImportMsg(`Imported ${r.created} test(s) from ${f.name}.`)
      loadSaved()
    } catch (e) {
      setImportMsg(`Import failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  const verdict = calc ? VERDICT_META[calc.verdict] : null

  return (
    <div>
      <div className="grid">
        <section className="card">
          <div className="card-head">
            <p className="eyebrow">Kill Switch</p>
            <h2>Test inputs</h2>
            <p className="muted">Prefilled with Neluna Test 1, real numbers from Nov 14–15. Edit any field — the verdict updates live.</p>
          </div>
          <label className="field">
            <span>Test name</span>
            <input value={testName} onChange={(e) => setTestName(e.target.value)} />
          </label>
          <div className="form-grid">
            {NUM_FIELDS.map((f) => (
              <label key={f.key} className="field">
                <span>{f.label}</span>
                <input
                  type="number"
                  step={f.step}
                  min={0}
                  value={input[f.key] as number}
                  onChange={(e) => setNum(f.key, e.target.value)}
                />
              </label>
            ))}
            <label className="field">
              <span>Currency</span>
              <select value={input.currency} onChange={(e) => setInput({ ...input, currency: e.target.value })}>
                <option>CAD</option>
                <option>USD</option>
              </select>
            </label>
          </div>
          <div className="row">
            <button className="btn primary" onClick={saveCurrent}>Save this test</button>
            <button
              className="btn"
              onClick={() => {
                setInput(NELUNA_TEST_1)
                setTestName('Neluna Test 1 — Nov 14-15')
              }}
            >
              Reset to Neluna Test 1
            </button>
            {savedMsg && <span className="muted">{savedMsg}</span>}
          </div>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="card verdict-card">
          <div className="verdict-top">
            <p className="eyebrow">Verdict</p>
            <h2>Diagnosis</h2>
            {calc && verdict ? (
              <>
                <div className="verdict-badge" style={{ color: verdict.color, background: verdict.bg, borderColor: verdict.border }}>
                  <span className="dot" />
                  {verdict.label}
                </div>
                <p className="verdict-sub">{testName} · {input.currency} · Spend {money(input.spend)} of {money(input.stop_loss)} stop loss</p>
              </>
            ) : null}
          </div>
          {calc && verdict ? (
            <>
              <ul className="reasoning">
                {calc.reasoning.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              <div className="stats">
                <div className="stat"><span>CTR</span><strong>{calc.ctr_pct}%</strong><em>target 1.5–2%+</em></div>
                <div className="stat"><span>CPC</span><strong>{money(calc.cpc)}</strong><em>per link click</em></div>
                <div className="stat"><span>LP → ATC</span><strong>{calc.lp_to_atc_pct}%</strong><em>target 2%+</em></div>
                <div className="stat"><span>CPA</span><strong>{money(calc.cpa)}</strong><em>per purchase</em></div>
                <div className="stat"><span>Break-even CPA</span><strong>{money(calc.break_even_cpa)}</strong><em>price − COGS − fees</em></div>
                <div className="stat"><span>Profit / loss</span><strong>{money(calc.profit)}</strong><em>after spend</em></div>
                <div className="stat"><span>Revenue</span><strong>{money(calc.revenue)}</strong><em>from purchases</em></div>
                <div className="stat"><span>ROAS</span><strong>{calc.roas.toFixed(2)}x</strong><em>revenue / spend</em></div>
              </div>
              <div className="stoploss">
                <div className="stoploss-head">
                  <span>Stop loss used</span>
                  <span>{money(input.spend)} of {money(input.stop_loss)} ({calc.stop_loss_pct}%)</span>
                </div>
                <div className="stoploss-bar">
                  <div
                    style={{
                      width: `${Math.min(calc.stop_loss_pct, 100)}%`,
                      background: calc.stop_loss_pct >= 100 ? '#991b1b' : calc.stop_loss_pct >= 75 ? '#92400e' : '#171717',
                    }}
                  />
                </div>
              </div>
            </>
          ) : (
            <p className="muted" style={{ padding: '0 24px 24px' }}>Calculating…</p>
          )}
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <p className="eyebrow">Funnel</p>
          <h2>Where does it break?</h2>
          <p className="muted">Each stage shows how much of the previous stage carried over. The break is where the carry-over collapses.</p>
        </div>
        <Funnel input={input} />
        {calc && (
          <p className="muted funnel-foot">
            Click → LP: {calc.click_to_lp_pct}% · LP → ATC: {calc.lp_to_atc_pct}% · ATC → purchase:{' '}
            {calc.atc_to_purchase_pct}%
          </p>
        )}
      </section>

      <section className="card">
        <div className="card-head">
          <p className="eyebrow">History</p>
          <h2>Saved tests</h2>
          <p className="muted">Load any saved test back into the calculator to compare verdicts.</p>
        </div>
        {saved.length === 0 ? (
          <p className="muted">No saved tests yet.</p>
        ) : (
          <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Name</th><th>Spend</th><th>CTR</th><th>LP→ATC</th><th>CPA</th><th>BE CPA</th><th>Verdict</th><th></th></tr>
            </thead>
            <tbody>
              {saved.map((t) => (
                <tr key={t.id}>
                  <td>{t.name}</td>
                  <td>{money(t.spend, t.currency)}</td>
                  <td>{t.calculation.ctr_pct}%</td>
                  <td>{t.calculation.lp_to_atc_pct}%</td>
                  <td>{money(t.calculation.cpa)}</td>
                  <td>{money(t.calculation.break_even_cpa)}</td>
                  <td><span className="badge" style={{ color: VERDICT_META[t.calculation.verdict].color, background: VERDICT_META[t.calculation.verdict].bg, border: `1px solid ${VERDICT_META[t.calculation.verdict].border}` }}>{VERDICT_META[t.calculation.verdict].label}</span></td>
                  <td className="row" style={{ marginTop: 0 }}>
                    <button className="btn small" onClick={() => loadTest(t)}>Load</button>
                    <button className="btn small danger" onClick={async () => { await api.deleteTest(t.id); loadSaved() }}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>

      <section className="card">
        <div className="card-head">
          <p className="eyebrow">Import</p>
          <h2>Import from Meta Ads Manager CSV</h2>
          <p className="muted">
            Export from Ads Manager, then paste or upload it. Columns: spend, impressions, clicks, lp_views, atc,
            purchases, ad_name. Missing columns default to 0 and are reported. Price / COGS come from the form above.
          </p>
        </div>
        <textarea rows={4} value={csvText} onChange={(e) => setCsvText(e.target.value)} />
        <div className="row">
          <button className="btn primary" onClick={doImport}>Import pasted CSV</button>
          <label className="btn">
            Upload CSV file
            <input type="file" accept=".csv" hidden onChange={(e) => onFile(e.target.files?.[0])} />
          </label>
          {importMsg && <span className="muted">{importMsg}</span>}
        </div>
      </section>
    </div>
  )
}

function AdSpy() {
  const [ads, setAds] = useState<CompetitorAd[]>([])
  const [summary, setSummary] = useState<BrandSummary[]>([])
  const [error, setError] = useState('')
  const [brand, setBrand] = useState('')
  const [country, setCountry] = useState('')
  const [format, setFormat] = useState('')
  const [source, setSource] = useState('')
  const [q, setQ] = useState('')
  const [form, setForm] = useState({
    brand: 'Cevera', ad_id: '', start_date: '2026-11-01', format: 'first-person story',
    country: 'CA', active: true, destination_url: '', source: 'brand_search', problem_word: '', notes: '',
  })
  const [formMsg, setFormMsg] = useState('')

  const load = useCallback(async () => {
    try {
      const params: Record<string, string> = {}
      if (brand) params.brand = brand
      if (country) params.country = country
      if (format) params.format = format
      if (source) params.source = source
      if (q) params.q = q
      const [a, s] = await Promise.all([api.listAds(params), api.summary()])
      setAds(a)
      setSummary(s)
    } catch {
      setError('Backend not reachable at http://localhost:8000 — start it first (see README).')
    }
  }, [brand, country, format, source, q])

  useEffect(() => {
    load()
  }, [load])

  const brands = useMemo(() => [...new Set(summary.map((s) => s.brand))], [summary])

  const submitAd = async () => {
    setFormMsg('')
    try {
      await api.createAd({ ...form, start_date: form.start_date || null })
      setFormMsg('Ad added.')
      load()
    } catch (e) {
      setFormMsg(`Failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  return (
    <div>
      <div className="notice">
        <p className="eyebrow">How this works</p>
        Meta Ad Library has no official API, so there is no live feed here.
        Check <a href="https://www.facebook.com/ads/library/" target="_blank" rel="noreferrer">facebook.com/ads/library</a> in
        your browser, then log the ads you find below. The 9 seeded rows are <strong>SAMPLE data</strong>, not verified
        Ad Library results. Longevity badge = running 90+ days.
      </div>
      {error && <p className="error">{error}</p>}

      <div className="summary-grid">
        {summary.map((s) => (
          <div key={s.brand} className="card summary-card">
            <p className="eyebrow">{s.brand}</p>
            <div className="big">{s.long_running_count} <span>long-running</span></div>
            <p className="muted">{s.total_ads} ads tracked · {s.active_ads} active · oldest {s.oldest_start_date || '—'}</p>
            <p>
              {Object.entries(s.formats).map(([f, n]) => (
                <span key={f} className="chip">{f}: {n}</span>
              ))}
            </p>
            <p className="muted">{Object.entries(s.countries).map(([c, n]) => `${c}: ${n}`).join(' · ')}</p>
          </div>
        ))}
      </div>

      <section className="card">
        <div className="card-head">
          <p className="eyebrow">Log an ad</p>
          <h2>Log an ad you found</h2>
          <p className="muted">Add it exactly as it appears in the Ad Library, including start date and format.</p>
        </div>
        <div className="form-grid">
          <label className="field"><span>Brand</span><input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} /></label>
          <label className="field"><span>Ad ID (optional)</span><input value={form.ad_id} onChange={(e) => setForm({ ...form, ad_id: e.target.value })} /></label>
          <label className="field"><span>Start date</span><input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></label>
          <label className="field"><span>Format</span>
            <select value={form.format} onChange={(e) => setForm({ ...form, format: e.target.value })}>
              {FORMATS.map((f) => <option key={f}>{f}</option>)}
            </select>
          </label>
          <label className="field"><span>Country</span>
            <select value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}>
              <option>CA</option><option>US</option>
            </select>
          </label>
          <label className="field"><span>Source</span>
            <select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}>
              <option value="brand_search">Brand search</option>
              <option value="problem_word_search">Problem-word search</option>
            </select>
          </label>
          <label className="field"><span>Problem word (if problem search)</span><input placeholder="e.g. neck pain" value={form.problem_word} onChange={(e) => setForm({ ...form, problem_word: e.target.value })} /></label>
          <label className="field"><span>Destination URL</span><input value={form.destination_url} onChange={(e) => setForm({ ...form, destination_url: e.target.value })} /></label>
        </div>
        <div className="row">
          <label className="field inline"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Active</label>
          <button className="btn primary" onClick={submitAd}>Add ad</button>
          {formMsg && <span className="muted">{formMsg}</span>}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <p className="eyebrow">Tracked ads</p>
          <h2>Tracked ads ({ads.length})</h2>
        </div>
        <div className="filters">
          <input placeholder="Search brand, format, problem word…" value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={brand} onChange={(e) => setBrand(e.target.value)}>
            <option value="">All brands</option>
            {brands.map((b) => <option key={b}>{b}</option>)}
          </select>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="">CA + US</option><option>CA</option><option>US</option>
          </select>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="">All formats</option>
            {FORMATS.map((f) => <option key={f}>{f}</option>)}
          </select>
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">Any source</option>
            <option value="brand_search">Brand search</option>
            <option value="problem_word_search">Problem-word search</option>
          </select>
        </div>
        {ads.length === 0 ? (
          <p className="muted">No ads match these filters.</p>
        ) : (
          <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Brand</th><th>Format</th><th>Country</th><th>Started</th><th>Days</th><th>Source</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {ads.map((a) => (
                <tr key={a.id}>
                  <td><strong>{a.brand}</strong>{a.problem_word && <div className="muted small">“{a.problem_word}”</div>}</td>
                  <td>{a.format}</td>
                  <td>{a.country}</td>
                  <td>{a.start_date || '—'}</td>
                  <td>{a.days_running ?? '—'} {a.is_long_running && <span className="badge winner">Winner · 90+ days</span>}</td>
                  <td>{a.source === 'brand_search' ? 'Brand search' : 'Problem-word search'}</td>
                  <td><span className={`status-dot${a.active ? '' : ' off'}`}>{a.active ? 'Active' : 'Inactive'}</span></td>
                  <td><button className="btn small danger" onClick={async () => { await api.deleteAd(a.id); load() }}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<'kill' | 'spy'>('kill')
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">AA</div>
          <div>
            <h1>Ad Autopsy</h1>
            <p>Kill Switch + Ad Spy for DTC brands. Built for Neluna — diagnose why a test failed before you kill it.</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Sections">
          <button className={tab === 'kill' ? 'active' : ''} onClick={() => setTab('kill')}>Kill Switch</button>
          <button className={tab === 'spy' ? 'active' : ''} onClick={() => setTab('spy')}>Ad Spy</button>
        </nav>
      </header>
      <main>{tab === 'kill' ? <KillSwitch /> : <AdSpy />}</main>
      <footer className="app-footer">
        <strong>Demo data:</strong> Neluna Test 1 is real (Nov 14–15, 2026). Competitor ads are SAMPLE rows, not live-verified
        Ad Library results — Meta Ad Library has no official API; log ads manually from the browser.
      </footer>
    </div>
  )
}
