import { useEffect, useMemo, useState, lazy, Suspense } from 'react'
import { NavbarMenu, type NavMenuItem } from './components/NavbarMenu'
import { API, fallbackCorridors, fallbackDistricts, getJSON, getExposure, postJSON, getDashboardSummary, probeReadiness } from './lib/api'
import type { District, ExposureRecord, ForecastPoint, ImageAnalysis, RainfallData, RiskPrediction, DashboardSummary } from './lib/api'
import './App.css'
import './interactions.css'

// Code-split heavy views to prevent blocking initial Overview paint
const RiskMap = lazy(() => import('./components/RiskMap'))
const ForecastSection = lazy(() => import('./components/ForecastSection'))
const FieldIntelligenceSection = lazy(() => import('./components/FieldIntelligenceSection'))
const ExplainabilitySection = lazy(() => import('./components/ExplainabilitySection'))
const VulnerabilitySection = lazy(() => import('./components/VulnerabilitySection'))
const SystemStatusSection = lazy(() => import('./components/SystemStatusSection'))

type Theme = 'light' | 'dark'
type ConnectionState = 'CONNECTING' | 'LIVE' | 'DEGRADED' | 'UNAVAILABLE'
type Corridor = { code: string; name: string; status: string; eta: string }

const navItems: NavMenuItem[] = [
  { label: 'Overview', target: 'overview-step' },
  { label: 'Risk Map', target: 'map-step' },
  { label: 'Forecast', target: 'forecast-step' },
  { label: 'Field Reports', target: 'field-step' },
  {
    label: 'More',
    target: '',
    menu: [
      { title: 'Vulnerability', description: 'District exposure & vulnerability scores', target: 'vuln-step' },
      { title: 'Explainability', description: 'Model factor decomposition & risk signals', target: 'xai-step' },
      { title: 'System Status & Advisory', description: 'Audio advisory & API connectivity', target: 'response-step' },
    ],
  },
]

function SectionSkeleton({ title }: { title: string }) {
  return (
    <div className="step-card card-skeleton-box" style={{ padding: '32px', textAlign: 'center' }}>
      <div className="subtext">Loading {title}...</div>
    </div>
  )
}

export function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [connectionState, setConnectionState] = useState<ConnectionState>('CONNECTING')
  const [mapInfoOpen, setMapInfoOpen] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>('')
  const [navOpen, setNavOpen] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'Overview' | 'Risk Map' | 'Forecast' | 'Field Reports' | 'Vulnerability' | 'Explainability' | 'System Status'>('Overview')
  const [region, setRegion] = useState('All North Eastern Region (NER)')
  const [layer, setLayer] = useState('Risk')
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null)
  const [districts, setDistricts] = useState<District[]>(fallbackDistricts)
  const [corridors, setCorridors] = useState<Corridor[]>(fallbackCorridors)
  const [refreshing, setRefreshing] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)
  const [reportLocation, setReportLocation] = useState('')
  const [reportLatitude, setReportLatitude] = useState('')
  const [reportLongitude, setReportLongitude] = useState('')
  const [reportDescription, setReportDescription] = useState('')
  const [reportSubmitting, setReportSubmitting] = useState(false)
  const [reportResult, setReportResult] = useState<any>(null)
  const [submittedReports, setSubmittedReports] = useState<any[]>([])
  const [reportImage, setReportImage] = useState<File | null>(null)
  const [reportImagePreview, setReportImagePreview] = useState<string | null>(null)
  const [imageAnalysis, setImageAnalysis] = useState<ImageAnalysis | null>(null)
  const [imageLoading, setImageLoading] = useState(false)
  const [imageError, setImageError] = useState<string | null>(null)
  const [riskPrediction, setRiskPrediction] = useState<RiskPrediction | null>(null)
  const [riskLoading, setRiskLoading] = useState(false)
  const [riskError, setRiskError] = useState<string | null>(null)
  const [exposureRecord, setExposureRecord] = useState<ExposureRecord | null>(null)
  const [forecast, setForecast] = useState<ForecastPoint[]>([])
  const [forecastSource, setForecastSource] = useState('')
  const [forecastLive, setForecastLive] = useState(false)
  const [forecastLoading, setForecastLoading] = useState(false)
  const [forecastError, setForecastError] = useState<string | null>(null)
  const [rainfallData, setRainfallData] = useState<RainfallData | null>(null)
  const [broadcastStatus, setBroadcastStatus] = useState<'idle' | 'broadcasting' | 'complete' | 'unavailable'>('idle')
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null)
  const [activeModelMeta, setActiveModelMeta] = useState<{ id: string; version: string; sha256: string } | null>(null)
  const [modelReadinessState, setModelReadinessState] = useState<'LOADING' | 'READY' | 'UNAVAILABLE'>('LOADING')

  const requestRiskPrediction = async (district: District) => {
    if (district.rainfall_3d == null || district.rainfall_7d == null) {
      setRiskPrediction(null)
      setRiskError('Risk prediction inputs are unavailable from the district feed.')
      return
    }

    setRiskLoading(true)
    setRiskError(null)

    try {
      const response = await postJSON<{ data: RiskPrediction }>('/api/risk', {
        latitude: district.lat,
        longitude: district.lng,
        rainfall_1d: district.rain24h,
        rainfall_3d: district.rainfall_3d,
        rainfall_7d: district.rainfall_7d,
        date: new Date().toISOString().slice(0, 10),
      })
      setRiskPrediction(response.data)
      setDistricts((current) =>
        current.map((d) =>
          d.id === district.id
            ? {
                ...d,
                riskScore: response.data.riskScore,
                status: response.data.status,
                confidence: response.data.confidence,
                modelSource: response.data.modelSource,
                factors: response.data.factors,
                decision: response.data.decision,
              }
            : d
        )
      )
    } catch {
      setRiskPrediction(null)
      setRiskError('Live risk prediction unavailable; showing district feed result.')
    } finally {
      setRiskLoading(false)
    }
  }

  const loadDistrictSignals = async (district: District) => {
    setForecastLoading(true)
    const [, rainfallResponse, forecastResponse, exposureResponse] = await Promise.allSettled([
      requestRiskPrediction(district),
      getJSON<RainfallData>(`/api/rainfall/current?latitude=${district.lat}&longitude=${district.lng}`),
      getJSON<{ forecast: ForecastPoint[]; source: string; is_live: boolean }>(`/api/forecast/${district.id}`),
      getExposure(district.id),
    ])
    if (rainfallResponse.status === 'fulfilled') setRainfallData(rainfallResponse.value)
    if (exposureResponse.status === 'fulfilled') setExposureRecord(exposureResponse.value)
    if (forecastResponse.status === 'fulfilled') {
      setForecast(forecastResponse.value.forecast)
      setForecastSource(forecastResponse.value.source)
      setForecastLive(forecastResponse.value.is_live)
      setForecastError(forecastResponse.value.is_live ? null : 'Forecast source unavailable.')
    } else {
      setForecast([])
      setForecastError('Forecast source unavailable.')
    }
    setForecastLoading(false)
  }

  const broadcastWarning = () => {
    if (!('speechSynthesis' in window)) {
      setBroadcastStatus('unavailable')
      return
    }

    if (broadcastStatus === 'broadcasting') {
      window.speechSynthesis.cancel()
      setBroadcastStatus('idle')
      return
    }

    window.speechSynthesis.cancel()
    const districtName = activeDistrict?.name || 'Selected District'
    const score = activeDistrict?.riskScore != null ? activeDistrict.riskScore : (riskPrediction?.riskScore ?? 0)
    const level = (activeDistrict?.decision || riskPrediction?.decision)?.riskLevel || (score >= 75 ? 'RED' : score >= 50 ? 'ORANGE' : score >= 35 ? 'YELLOW' : 'GREEN')

    let speechText = ''
    if (level === 'RED') {
      speechText = `NexSolve notice for ${districtName}. Current risk score is ${score} out of 100. Status: Emergency level.`
    } else if (level === 'ORANGE') {
      speechText = `NexSolve notice for ${districtName}. Current risk score is ${score} out of 100. Status: Warning level.`
    } else if (level === 'YELLOW') {
      speechText = `NexSolve notice for ${districtName}. Current risk score is ${score} out of 100. Status: Elevated level.`
    } else {
      speechText = `NexSolve notice for ${districtName}. Current risk score is ${score} out of 100. Status: Nominal.`
    }

    try {
      const utterance = new SpeechSynthesisUtterance(speechText)
      utterance.rate = 0.95
      utterance.onstart = () => setBroadcastStatus('broadcasting')
      utterance.onend = () => setBroadcastStatus('idle')
      utterance.onerror = () => setBroadcastStatus('unavailable')
      setBroadcastStatus('broadcasting')
      window.speechSynthesis.speak(utterance)
    } catch {
      setBroadcastStatus('unavailable')
    }
  }

  const handleWarmupAndRefresh = async (isManual = false) => {
    setRefreshing(true)
    if (isManual || connectionState !== 'LIVE') {
      setConnectionState('CONNECTING')
    }

    try {
      const probeRes = await probeReadiness()
      if (probeRes.ready && probeRes.model_id && probeRes.model_version && probeRes.model_sha256) {
        setActiveModelMeta({
          id: probeRes.model_id,
          version: probeRes.model_version,
          sha256: probeRes.model_sha256,
        })
        setModelReadinessState('READY')
      } else if (probeRes.model_id && probeRes.model_version) {
        setActiveModelMeta({
          id: probeRes.model_id,
          version: probeRes.model_version,
          sha256: probeRes.model_sha256 || '',
        })
        setModelReadinessState('READY')
      } else {
        setActiveModelMeta(null)
        setModelReadinessState('UNAVAILABLE')
      }

      const [corridorResponse, summaryResponse, districtsResponse] = await Promise.allSettled([
        getJSON<{ data: Corridor[] }>('/api/corridors', {}, 3),
        getDashboardSummary().catch(() => null),
        getJSON<{ data: District[] }>('/api/districts', {}, 3),
      ])

      if (corridorResponse.status === 'fulfilled') {
        setCorridors(corridorResponse.value.data)
      }
      if (summaryResponse.status === 'fulfilled' && summaryResponse.value) {
        setDashboardSummary(summaryResponse.value)
      }
      if (districtsResponse.status === 'fulfilled') {
        setDistricts(districtsResponse.value.data)
      }

      const isConnected = probeRes.ready || summaryResponse.status === 'fulfilled' || corridorResponse.status === 'fulfilled'
      setConnectionState(isConnected ? 'LIVE' : 'DEGRADED')
      setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
    } catch {
      setActiveModelMeta(null)
      setModelReadinessState('UNAVAILABLE')
      setConnectionState('DEGRADED')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    const defaultDistrict = fallbackDistricts.find((d) => d.id === 'champhai') || fallbackDistricts[0]
    if (defaultDistrict && !selectedDistrictId) {
      setSelectedDistrictId(defaultDistrict.id)
    }
    void handleWarmupAndRefresh(false)
  }, [])

  useEffect(() => {
    if (activeTab === 'Risk Map') {
      getJSON<{ data: District[] }>('/api/districts')
        .then((res) => setDistricts(res.data))
        .catch(() => {})
    }
  }, [activeTab])

  useEffect(() => {
    if (!selectedDistrictId) return
    const selected = districts.find((d) => d.id === selectedDistrictId)
    if (selected) {
      void loadDistrictSignals(selected)
    }
  }, [selectedDistrictId])

  const activeDistrict = useMemo(() => {
    return districts.find((d) => d.id === selectedDistrictId) || districts[0]
  }, [districts, selectedDistrictId])

  const filteredDistricts = useMemo(() => {
    if (region === 'All North Eastern Region (NER)') return districts
    return districts.filter((d) => d.state.toLowerCase() === region.toLowerCase() || region.includes(d.state))
  }, [districts, region])

  const highestRiskDistrict = useMemo(() => {
    if (!districts.length) return null
    return [...districts].sort((a, b) => (b.riskScore ?? 0) - (a.riskScore ?? 0))[0]
  }, [districts])

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) {
      setReportImage(null)
      setReportImagePreview(null)
      setImageAnalysis(null)
      setImageError(null)
      return
    }

    setReportImage(file)
    setImageError(null)
    setImageLoading(true)

    const reader = new FileReader()
    reader.onloadend = () => {
      setReportImagePreview(reader.result as string)
    }
    reader.readAsDataURL(file)

    const formData = new FormData()
    formData.append('file', file)

    fetch(`${API}/api/cv/analyze`, {
      method: 'POST',
      body: formData,
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Image API ${res.status}`)
        return res.json()
      })
      .then((data: ImageAnalysis) => {
        setImageAnalysis(data)
      })
      .catch(() => {
        setImageError('Image screening service unavailable; report queued for manual review.')
        setImageAnalysis(null)
      })
      .finally(() => {
        setImageLoading(false)
      })
  }

  const submitReport = async () => {
    if (!reportLocation.trim() || !reportDescription.trim()) return

    setReportSubmitting(true)
    setReportResult(null)

    try {
      const body = new FormData()
      body.append('type', 'Landslide Observation')
      body.append('location', reportLocation)
      if (reportLatitude) body.append('latitude', reportLatitude)
      if (reportLongitude) body.append('longitude', reportLongitude)
      body.append('description', reportDescription)
      if (reportImage) body.append('file', reportImage)

      const response = await fetch(`${API}/api/reports`, {
        method: 'POST',
        body,
      })

      if (!response.ok) throw new Error(`Report API ${response.status}`)
      const result = await response.json()
      setReportResult(result.report)
      setSubmittedReports((current) => [result.report, ...current.filter((report) => report.id !== result.report.id)])
    } catch {
      setReportResult({
        verified: false,
        verificationStatus: 'SERVICE UNAVAILABLE',
        verificationConfidence: null,
        severity: 'UNKNOWN',
        landslideClassification: 'NOT AVAILABLE',
        recommendedAction: 'Report queued locally.',
      })
    } finally {
      setReportSubmitting(false)
    }
  }

  const handleNavClick = (target: string, label?: string) => {
    setNavOpen(null)
    if (label === 'Risk Map' || target === 'map-step') setActiveTab('Risk Map')
    else if (label === 'Forecast' || target === 'forecast-step') setActiveTab('Forecast')
    else if (label === 'Field Reports' || target === 'field-step') setActiveTab('Field Reports')
    else if (target === 'vuln-step') setActiveTab('Vulnerability')
    else if (target === 'xai-step') setActiveTab('Explainability')
    else if (target === 'response-step' || target === 'status-step' || target === 'alerts-step' || label === 'System Status & Advisory') setActiveTab('System Status')
    else setActiveTab('Overview')
  }

  const getDistrictStatusBadgeClass = (district: District | null) => {
    if (!district) return 'green'
    const level = district.decision?.riskLevel
    const score = district.riskScore ?? 0
    if (level === 'RED' || score >= 75) return 'red'
    if (level === 'ORANGE' || score >= 50) return 'orange'
    if (level === 'YELLOW' || score >= 35) return 'yellow'
    return 'green'
  }

  const getDistrictStatusLabel = (district: District | null) => {
    if (!district) return 'NOMINAL'
    const level = district.decision?.riskLevel
    const score = district.riskScore ?? 0
    if (level === 'RED' || score >= 75) return 'EMERGENCY'
    if (level === 'ORANGE' || score >= 50) return 'WARNING'
    if (level === 'YELLOW' || score >= 35) return 'ELEVATED'
    return 'NOMINAL'
  }

  return (
    <div className="app-shell">
      {/* Top Header Navigation */}
      <header className="topbar">
        <div className="topbar-left">
          <div className="brand">
            <span className="brand-mark">N</span>
            <div className="brand-text">
              <span className="brand-title">NexSolve</span>
              <span className="brand-subtitle">Risk Intelligence</span>
            </div>
          </div>
        </div>

        <NavbarMenu
          items={navItems}
          activeTab={activeTab}
          openLabel={navOpen}
          onOpenChange={(l) => setNavOpen(l)}
          onNavigate={(target) => handleNavClick(target)}
        />

        <div className="topbar-right">
          <select value={region} onChange={(e) => setRegion(e.target.value)} className="region-select">
            <option value="All North Eastern Region (NER)">All NER</option>
            <option value="Mizoram">Mizoram</option>
            <option value="Manipur">Manipur</option>
            <option value="Meghalaya">Meghalaya</option>
            <option value="Arunachal Pradesh">Arunachal Pradesh</option>
            <option value="Nagaland">Nagaland</option>
            <option value="Assam">Assam</option>
            <option value="Tripura">Tripura</option>
            <option value="Sikkim">Sikkim</option>
          </select>

          <div className={`status-pill ${connectionState.toLowerCase()}`}>
            <span className="status-dot" />
            {connectionState === 'LIVE' ? 'LIVE' : connectionState === 'CONNECTING' ? 'CONNECTING' : 'DEGRADED'}
          </div>

          <button className="refresh-button" disabled={refreshing} onClick={() => void handleWarmupAndRefresh(true)}>
            {refreshing ? 'Updating…' : lastUpdated ? lastUpdated : 'Refresh'}
          </button>

          <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <main className="main-content">
        {/* VIEW 1: OVERVIEW DASHBOARD */}
        {activeTab === 'Overview' && (
          <div className="overview-view">
            {/* Minimal High-Visibility Executive Summary Metrics Strip */}
            <div className="metrics-summary-strip">
              <div className="summary-metric-card">
                <div className="metric-header">
                  <span className="metric-kicker">HIGHEST RISK NODE</span>
                  <span className={`risk-badge level-${getDistrictStatusBadgeClass(highestRiskDistrict)}`}>
                    {getDistrictStatusLabel(highestRiskDistrict)}
                  </span>
                </div>
                <div className="metric-val-large">{highestRiskDistrict?.riskScore ?? 0} <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>/ 100</span></div>
                <div className="metric-sub-label">{highestRiskDistrict?.name || 'Champhai Axis'}</div>
              </div>

              <div className="summary-metric-card">
                <div className="metric-header">
                  <span className="metric-kicker">24H PEAK RAINFALL</span>
                  <span className={`risk-badge ${rainfallData?.is_live ? 'level-green' : 'level-yellow'}`}>
                    {rainfallData?.is_live ? 'LIVE FEED' : 'DEGRADED'}
                  </span>
                </div>
                <div className="metric-val-large">{rainfallData?.rainfall_24h ?? activeDistrict?.rain24h ?? 0} <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>mm</span></div>
                <div className="metric-sub-label">{rainfallData?.source || 'Open-Meteo API'}</div>
              </div>

              <div className="summary-metric-card">
                <div className="metric-header">
                  <span className="metric-kicker">ROAD CORRIDORS</span>
                  <span className="risk-badge level-blue">MoRTH REGISTRY</span>
                </div>
                <div className="metric-val-large">4 <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>AXES</span></div>
                <div className="metric-sub-label">2 Blocked · 1 Restricted · 1 Open</div>
              </div>

              <div className="summary-metric-card">
                <div className="metric-header">
                  <span className="metric-kicker">SPATIAL COVERAGE</span>
                  <span className="risk-badge level-green">SoI ABDB</span>
                </div>
                <div className="metric-val-large">131 <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>DISTRICTS</span></div>
                <div className="metric-sub-label">9 Operational Nodes · 16 Profiled</div>
              </div>
            </div>

            {/* Structured 2-Column Operational Grid */}
            <div className="overview-dashboard-grid">
              <div className="overview-main-panel">
                {/* Operational Nodes Table */}
                <div className="panel-box">
                  <div className="panel-box-header">
                    <h3>Operational Locations ({filteredDistricts.length})</h3>
                    <span className="subtext">Click row to inspect signals</span>
                  </div>
                  <table className="node-table">
                    <thead>
                      <tr>
                        <th>Location & State</th>
                        <th>24h Rain</th>
                        <th>Slope</th>
                        <th>GSI Events</th>
                        <th>Risk Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDistricts.map((d) => (
                        <tr
                          key={d.id}
                          className={selectedDistrictId === d.id ? 'selected' : ''}
                          onClick={() => setSelectedDistrictId(d.id)}
                        >
                          <td>
                            <div className="node-name-cell">{d.name}</div>
                            <div className="node-state-sub">{d.state}</div>
                          </td>
                          <td>{d.rain24h != null ? `${d.rain24h} mm` : 'N/A'}</td>
                          <td>{d.slopeAngle != null ? `${d.slopeAngle.toFixed(1)}°` : 'N/A'}</td>
                          <td>{d.gsiEvents}</td>
                          <td>
                            <span className={`risk-badge level-${getDistrictStatusBadgeClass(d)}`}>
                              {getDistrictStatusLabel(d)} ({d.riskScore ?? 0})
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Active District Inspector */}
                {activeDistrict && (
                  <div className="district-inspector-card">
                    <div className="inspector-header">
                      <div className="inspector-title-group">
                        <h3>{activeDistrict.name} — {activeDistrict.state}</h3>
                        <div className="inspector-sub">
                          {activeDistrict.lat.toFixed(4)}°N, {activeDistrict.lng.toFixed(4)}°E · Slope {activeDistrict.slopeAngle.toFixed(1)}°
                        </div>
                      </div>
                      <span className={`risk-badge level-${getDistrictStatusBadgeClass(activeDistrict)}`}>
                        {getDistrictStatusLabel(activeDistrict)} ({activeDistrict.riskScore ?? 0})
                      </span>
                    </div>

                    <div className="inspector-metrics-grid">
                      <div className="inspector-metric-item">
                        <span>24h Rainfall</span>
                        <strong>{activeDistrict.rain24h != null ? `${activeDistrict.rain24h} mm` : 'N/A'}</strong>
                      </div>
                      <div className="inspector-metric-item">
                        <span>Terrain Slope</span>
                        <strong>{activeDistrict.slopeAngle != null ? `${activeDistrict.slopeAngle.toFixed(1)}°` : 'N/A'}</strong>
                      </div>
                      <div className="inspector-metric-item">
                        <span>Historical GSI Events</span>
                        <strong>{activeDistrict.gsiEvents}</strong>
                      </div>
                      <div className="inspector-metric-item">
                        <span>Model Source</span>
                        <strong>{activeDistrict.modelSource && activeDistrict.modelSource !== 'uninitialized' && activeDistrict.modelSource !== 'Loading…' ? activeDistrict.modelSource : activeModelMeta ? `Random Forest v${activeModelMeta.version}` : modelReadinessState === 'LOADING' ? 'Loading…' : 'Unavailable'}</strong>
                      </div>
                    </div>

                    <div className="inspector-actions">
                      <button className="btn-primary" onClick={broadcastWarning}>
                        {broadcastStatus === 'broadcasting' ? '🔊 Stop Audio Advisory' : '🔊 Listen to Advisory'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Side Panels Column */}
              <div className="overview-side-panel">
                {/* Road Corridors Panel */}
                <div className="panel-box">
                  <div className="panel-box-header">
                    <h3>Road Corridors</h3>
                    <span className="subtext">MoRTH Registry</span>
                  </div>
                  <div className="corridor-list">
                    {corridors.slice(0, 4).map((c) => (
                      <div key={c.code} className="corridor-row">
                        <div>
                          <span className="corridor-code">{c.code}</span>
                          <span className="corridor-name">{c.name}</span>
                        </div>
                        <span className={`corridor-status-tag ${c.status.toLowerCase()}`}>
                          {c.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Spatial Framework Intelligence */}
                <div className="panel-box">
                  <div className="panel-box-header">
                    <h3>Spatial Framework</h3>
                    <span className="subtext">SoI ABDB</span>
                  </div>
                  <div style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Official Districts</span>
                      <strong>{dashboardSummary?.monitored_districts_count ?? 131}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Operational Risk Nodes</span>
                      <strong>{dashboardSummary?.operational_nodes_count ?? 9}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Profiled Exposure</span>
                      <strong>16 / 131 Profiled</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: RISK MAP */}
        {activeTab === 'Risk Map' && (
          <Suspense fallback={<SectionSkeleton title="Risk Map" />}>
            <RiskMap
              districts={filteredDistricts}
              corridors={corridors}
              selectedDistrictId={selectedDistrictId}
              setSelectedDistrictId={setSelectedDistrictId}
              layer={layer}
              setLayer={setLayer}
              mapInfoOpen={mapInfoOpen}
              setMapInfoOpen={setMapInfoOpen}
            />
          </Suspense>
        )}

        {/* VIEW 3: FORECAST */}
        {activeTab === 'Forecast' && (
          <Suspense fallback={<SectionSkeleton title="Risk Forecast" />}>
            <ForecastSection
              activeDistrict={activeDistrict}
              forecast={forecast}
              forecastSource={forecastSource}
              forecastLive={forecastLive}
              forecastLoading={forecastLoading}
              forecastError={forecastError}
            />
          </Suspense>
        )}

        {/* VIEW 4: FIELD REPORTS */}
        {activeTab === 'Field Reports' && (
          <Suspense fallback={<SectionSkeleton title="Field Reports" />}>
            <FieldIntelligenceSection
              reportOpen={reportOpen}
              setReportOpen={setReportOpen}
              reportLocation={reportLocation}
              setReportLocation={setReportLocation}
              reportLatitude={reportLatitude}
              setReportLatitude={setReportLatitude}
              reportLongitude={reportLongitude}
              setReportLongitude={setReportLongitude}
              reportDescription={reportDescription}
              setReportDescription={setReportDescription}
              reportSubmitting={reportSubmitting}
              reportResult={reportResult}
              submittedReports={submittedReports}
              reportImage={reportImage}
              reportImagePreview={reportImagePreview}
              imageAnalysis={imageAnalysis}
              imageLoading={imageLoading}
              imageError={imageError}
              handleImageChange={handleImageChange}
              submitReport={submitReport}
            />
          </Suspense>
        )}

        {/* VIEW 5: VULNERABILITY */}
        {activeTab === 'Vulnerability' && (
          <Suspense fallback={<SectionSkeleton title="Vulnerability Profiles" />}>
            <VulnerabilitySection activeDistrict={activeDistrict} exposureRecord={exposureRecord} />
          </Suspense>
        )}

        {/* VIEW 6: EXPLAINABILITY */}
        {activeTab === 'Explainability' && (
          <Suspense fallback={<SectionSkeleton title="Explainability" />}>
            <ExplainabilitySection activeDistrict={activeDistrict} riskPrediction={riskPrediction} riskLoading={riskLoading} riskError={riskError} />
          </Suspense>
        )}

        {/* VIEW 7: SYSTEM STATUS & ADVISORY */}
        {activeTab === 'System Status' && (
          <Suspense fallback={<SectionSkeleton title="System Status" />}>
            <SystemStatusSection
              connectionState={connectionState}
              activeModelMeta={activeModelMeta}
              modelReadinessState={modelReadinessState}
              rainfallData={rainfallData}
              dashboardSummary={dashboardSummary}
              lastUpdated={lastUpdated}
              broadcastStatus={broadcastStatus}
              broadcastWarning={broadcastWarning}
              handleWarmupAndRefresh={handleWarmupAndRefresh}
            />
          </Suspense>
        )}
      </main>

      <footer className="footer-bar">
        <span>NexSolve Disaster Management © 2026</span>
        <span>
          Model: {
            modelReadinessState === 'LOADING'
              ? 'Loading…'
              : modelReadinessState === 'UNAVAILABLE' || !activeModelMeta
              ? 'Unavailable'
              : `Random Forest v${activeModelMeta.version} · ${activeModelMeta.id} (SHA-256: ${activeModelMeta.sha256 ? `${activeModelMeta.sha256.slice(0, 9)}...` : 'Unavailable'})`
          }
        </span>
      </footer>
    </div>
  )
}

export default App
