import { useEffect, useMemo, useState } from 'react'
import toast, { Toaster } from 'react-hot-toast'
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function PriorityBadge({ level }) {
  const value = (level || '').toString().toLowerCase()
  const normalized = value === 'high' || value === 'medium' || value === 'low' ? value : 'low'
  return <span className={`priority-badge ${normalized}`}>{normalized}</span>
}

function App() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved === 'light' || saved === 'dark' ? saved : 'dark'
  })
  const [complaint, setComplaint] = useState('')
  const [loading, setLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [lastComplaint, setLastComplaint] = useState('')
  const [history, setHistory] = useState([])
  const [issueFilter, setIssueFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const canSubmit = useMemo(() => complaint.trim().length > 0 && !loading, [complaint, loading])
  const issuePhraseByType = useMemo(
    () => ({
      power_cut: [
        'power cut',
        'no power',
        'no electricity',
        'light gone',
        'current not coming',
        'no supply',
        'blackout',
      ],
      voltage_issue: ['low voltage', 'high voltage', 'voltage drop', 'fluctuating voltage', 'voltage problem'],
      transformer_fault: ['transformer blast', 'transformer burst', 'burnt transformer', 'sparks near transformer'],
      billing_issue: ['wrong bill', 'bill too high', 'overcharged', 'extra charge', 'unexpected bill'],
      wire_issue: ['wire cut', 'wire broken', 'cable cut', 'hanging wire', 'wire sparking'],
      meter_issue: ['meter not working', 'meter not running', 'meter stuck', 'reading wrong'],
    }),
    [],
  )
  const filteredHistory = useMemo(() => {
    return history.filter((item) => {
      const issueMatch = issueFilter === 'all' || item?.issue === issueFilter
      const priorityMatch = priorityFilter === 'all' || item?.priority === priorityFilter
      return issueMatch && priorityMatch
    })
  }, [history, issueFilter, priorityFilter])

  const issueFilterOptions = useMemo(() => {
    const values = [...new Set(history.map((item) => item?.issue).filter(Boolean))]
    return values.sort()
  }, [history])

  const summaryStats = useMemo(() => {
    const totalComplaints = filteredHistory.length
    const highPriorityCount = filteredHistory.filter((item) => (item?.priority || '').toLowerCase() === 'high').length

    const issueCounts = {}
    for (const item of filteredHistory) {
      const issue = item?.issue || 'unknown'
      issueCounts[issue] = (issueCounts[issue] || 0) + 1
    }
    const mostCommonIssue =
      Object.entries(issueCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'

    return { totalComplaints, highPriorityCount, mostCommonIssue }
  }, [filteredHistory])

  const prioritySummary = useMemo(() => {
    const seed = { high: 0, medium: 0, low: 0 }
    for (const item of filteredHistory) {
      const level = (item?.priority || '').toLowerCase()
      if (level in seed) seed[level] += 1
    }
    return seed
  }, [filteredHistory])

  const priorityData = useMemo(() => {
    const seed = { high: 0, medium: 0, low: 0 }
    for (const item of filteredHistory) {
      const level = (item?.priority || '').toLowerCase()
      if (level in seed) seed[level] += 1
    }
    return [
      { name: 'High', value: seed.high, key: 'high' },
      { name: 'Medium', value: seed.medium, key: 'medium' },
      { name: 'Low', value: seed.low, key: 'low' },
    ].filter((d) => d.value > 0)
  }, [filteredHistory])

  const issueTypeData = useMemo(() => {
    const counts = {}
    for (const item of filteredHistory) {
      const issue = item?.issue || 'unknown'
      counts[issue] = (counts[issue] || 0) + 1
    }
    return Object.entries(counts).map(([issue, count]) => ({ issue, count }))
  }, [filteredHistory])

  const fetchHistory = async () => {
    setHistoryLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/complaints`)
      if (!response.ok) {
        throw new Error('Failed to load complaint history.')
      }
      const data = await response.json()
      setHistory(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Unable to fetch complaint history.')
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setResult(null)

    const text = complaint.trim()
    if (!text) {
      setError('Please enter a complaint before submitting.')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ complaint: text }),
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || 'Failed to analyze complaint.')
      }

      setResult(data)
      setLastComplaint(text)
      setComplaint('')
      toast.success('Complaint analyzed successfully')
      await fetchHistory()
    } catch (err) {
      toast.error('Something went wrong')
      setError(err.message || 'Unexpected error while analyzing complaint.')
    } finally {
      setLoading(false)
    }
  }

  const highlightedComplaint = useMemo(() => {
    if (!result || !lastComplaint) return ''

    const sourceText = lastComplaint
    const sourceLower = sourceText.toLowerCase()
    const issueType = result?.issue_type
    const issueCandidates = issuePhraseByType[issueType] || []

    let issuePhrase = ''
    for (const phrase of issueCandidates) {
      if (sourceLower.includes(phrase.toLowerCase())) {
        issuePhrase = phrase
        break
      }
    }

    const safeReplace = (text, phrase, className) => {
      if (!phrase || phrase.toLowerCase() === 'unknown') return text
      const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const regex = new RegExp(`(${escaped})`, 'ig')
      return text.replace(regex, `<mark class="${className}">$1</mark>`)
    }

    let output = sourceText
    output = safeReplace(output, issuePhrase, 'hl-issue')
    output = safeReplace(output, result?.location, 'hl-location')
    return output
  }, [result, lastComplaint, issuePhraseByType])

  const chartAxisTick = useMemo(() => ({ fill: 'var(--text)', fontSize: 11 }), [])
  const tooltipStyle = useMemo(
    () => ({
      background: 'var(--tooltip-bg)',
      color: 'var(--tooltip-text)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      boxShadow: 'var(--shadow-2)',
    }),
    [],
  )

  return (
    <div className="app-shell">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--card)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
          },
        }}
      />
      <header className="top-header">
        <div className="top-header-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true" />
            <div className="brand-text">
              <h1>Smart Electricity Complaint Analyzer</h1>
              <p className="subtitle">Analyze issues, detect urgency, and track complaint history.</p>
            </div>
          </div>
          <div className="header-actions">
            <div className="env-pill" title={`API: ${API_BASE_URL}`}>
              API: {API_BASE_URL.replace(/^https?:\/\//, '')}
            </div>
            <button
              type="button"
              className="secondary toggle"
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              aria-label="Toggle dark mode"
              title="Toggle dark mode"
            >
              {theme === 'dark' ? 'Dark' : 'Light'}
            </button>
          </div>
        </div>
      </header>

      <main className="container">
        {error && <div className="alert error">{error}</div>}

        <section className="summary-grid">
          <div className="summary-card total">
            <div className="summary-label">Total Complaints</div>
            <div className="summary-value">{summaryStats.totalComplaints}</div>
          </div>
          <div className="summary-card high">
            <div className="summary-label">High Priority Complaints</div>
            <div className="summary-value">{summaryStats.highPriorityCount}</div>
          </div>
          <div className="summary-card common">
            <div className="summary-label">Most Common Issue Type</div>
            <div className="summary-value compact">{summaryStats.mostCommonIssue}</div>
          </div>
        </section>

        <section className="card card-pad filter-card">
          <div className="card-header row">
            <div>
              <h2>Filters</h2>
              <p className="muted">Filter by issue type and priority.</p>
            </div>
          </div>
          <div className="filters-grid">
            <div className="filter-field">
              <label htmlFor="issueFilter">Issue Type</label>
              <select id="issueFilter" value={issueFilter} onChange={(e) => setIssueFilter(e.target.value)}>
                <option value="all">All</option>
                {issueFilterOptions.map((issue) => (
                  <option key={issue} value={issue}>
                    {issue}
                  </option>
                ))}
              </select>
            </div>
            <div className="filter-field">
              <label htmlFor="priorityFilter">Priority</label>
              <select id="priorityFilter" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
                <option value="all">All</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </section>

        <section className="card card-pad insights-card">
          <div className="card-header">
            <h2>Insights</h2>
            <p className="muted">Real-time summary from filtered complaints.</p>
          </div>
          <div className="insights-grid">
            <div className="insight-item">
              <span className="insight-key">Most Frequent Issue</span>
              <span className="insight-value">{summaryStats.mostCommonIssue}</span>
            </div>
            <div className="insight-item">
              <span className="insight-key">Priority Distribution</span>
              <span className="insight-value">
                High: {prioritySummary.high} | Medium: {prioritySummary.medium} | Low: {prioritySummary.low}
              </span>
            </div>
          </div>
        </section>

        <div className="dashboard">
          <section className="panel left">
            <form className="card card-pad" onSubmit={onSubmit}>
              <div className="card-header">
                <h2>Submit Complaint</h2>
                <p className="muted">Paste the complaint text exactly as received.</p>
              </div>

              <label htmlFor="complaint">Complaint Text</label>
              <textarea
                id="complaint"
                value={complaint}
                onChange={(e) => setComplaint(e.target.value)}
                placeholder="Example: Power cut in Banani for 3 hours, no electricity."
                rows={8}
              />

              <div className="actions">
                <button type="submit" disabled={!canSubmit}>
                  {loading ? 'Analyzing...' : 'Analyze & Save'}
                </button>
              </div>
              {loading && (
                <div className="loading-state" role="status" aria-live="polite">
                  <span className="spinner" aria-hidden="true" />
                  <span>Analyzing...</span>
                </div>
              )}
            </form>

            <section className="card card-pad">
              <div className="card-header">
                <h2>Complaint Insights</h2>
                <p className="muted">Charts based on complaint history.</p>
              </div>

              {historyLoading ? (
                <p className="muted">Loading charts...</p>
              ) : filteredHistory.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon" aria-hidden="true">📭</div>
                  <div className="empty-title">No complaints yet</div>
                  <div className="empty-subtitle">Submit a complaint to see analytics</div>
                </div>
              ) : (
                <div className="charts-grid">
                  <div className="chart-card">
                    <h3>Priority Distribution</h3>
                    <div className="chart-wrap">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={priorityData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={74}
                            innerRadius={40}
                            paddingAngle={2}
                          >
                            {priorityData.map((entry) => (
                              <Cell
                                key={entry.key}
                                fill={
                                  entry.key === 'high'
                                    ? 'var(--danger)'
                                    : entry.key === 'medium'
                                      ? 'var(--warning)'
                                      : 'var(--success)'
                                }
                              />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--tooltip-text)' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="chart-card">
                    <h3>Issue Types</h3>
                    <div className="chart-wrap">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={issueTypeData} margin={{ top: 8, right: 8, left: -12, bottom: 8 }}>
                          <XAxis dataKey="issue" tick={chartAxisTick} axisLine={{ stroke: 'var(--border)' }} />
                          <YAxis
                            allowDecimals={false}
                            tick={chartAxisTick}
                            axisLine={{ stroke: 'var(--border)' }}
                            tickLine={{ stroke: 'var(--border)' }}
                          />
                          <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--tooltip-text)' }} />
                          <Bar dataKey="count" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}
            </section>
          </section>

          <section className="panel right">
            <section className="card card-pad">
              <div className="card-header">
                <h2>Analysis Output</h2>
                <p className="muted">Most recent analysis result.</p>
              </div>

              {!result ? (
                <p className="muted">No analysis yet. Submit a complaint to see results.</p>
              ) : (
                <div className="result-grid">
                  <div className="kpi">
                    <div className="kpi-label">Issue Type</div>
                    <div className="kpi-value">{result.issue_type}</div>
                  </div>
                  <div className="kpi">
                    <div className="kpi-label">Location</div>
                    <div className="kpi-value">{result.location}</div>
                  </div>
                  <div className="kpi">
                    <div className="kpi-label">Priority</div>
                    <PriorityBadge level={result.priority} />
                  </div>

                  <div className="divider" />

                  <div className="suggested">
                    <div className="kpi-label">Highlighted Complaint</div>
                    <div
                      className="suggested-text highlighted-block"
                      dangerouslySetInnerHTML={{ __html: highlightedComplaint }}
                    />
                  </div>

                  <div className="suggested">
                    <div className="kpi-label">Suggested Action</div>
                    <div className="suggested-text">{result.suggested_action}</div>
                  </div>
                </div>
              )}
            </section>

            <section className="card card-pad">
              <div className="card-header row">
                <div>
                  <h2>Complaint History</h2>
                  <p className="muted">Stored in SQLite via the backend.</p>
                </div>
                <button type="button" className="secondary" onClick={fetchHistory} disabled={historyLoading}>
                  {historyLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>

              {historyLoading ? (
                <p className="muted">Loading history...</p>
              ) : filteredHistory.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon" aria-hidden="true">📥</div>
                  <div className="empty-title">No complaints yet</div>
                  <div className="empty-subtitle">Submit a complaint to see analytics</div>
                </div>
              ) : (
                <ul className="history-list">
                  {filteredHistory.map((item) => (
                    <li key={item.id} className="history-item">
                      <div className="history-top">
                        <p className="history-text">{item.complaint}</p>
                        <PriorityBadge level={item.priority} />
                      </div>
                      <p className="history-meta">
                        Issue: <strong>{item.issue}</strong> · Location: <strong>{item.location}</strong>
                      </p>
                      <p className="history-time">{new Date(item.timestamp).toLocaleString()}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
