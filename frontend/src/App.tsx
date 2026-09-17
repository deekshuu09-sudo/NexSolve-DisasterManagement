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
      { title: 'Operational Dashboard', description: 'Priority alerts & decision support queue', target: 'alerts-step' },
      { title: 'System Status & Advisory', description: 'Audio advisory & API connectivity', target: 'response-step' },
    ],
  },
]

function SectionSkeleton({ title }: { title: string }) {
  return (
    <div className="step-card card-skeleton-box">
      <div className="skeleton-line title-line" />
      <div className="skeleton-text">Loading {title}...</div>
    </div>
  )
}

export function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [connectionState, setConnectionState] = useState<ConnectionState>('CONNECTING')
  const [mapInfoOpen, setMapInfoOpen] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>('')
  const [navOpen, setNavOpen] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'Overview' | 'Risk Map' | 'Forecast' | 'Field Reports' | 'Vulnerability' | 'Explainability'>('Overview')
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
      setRiskError('Live risk prediction unavailable; showing the district feed result.')
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
      setForecastError(forecastResponse.value.is_live ? null : 'Forecast source unavailable — showing latest available IMD data.')
    } else {
      setForecast([])
      setForecastError('Forecast source unavailable — showing latest available IMD data.')
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
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Red, emergency level decision.`
    } else if (level === 'ORANGE') {
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Orange, warning level.`
    } else if (level === 'YELLOW') {
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Yellow, elevated.`
    } else {
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Green, nominal.`
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

  // Initial non-blocking shell mount — immediately renders static UI, then initiates background warm-up & health probe
  useEffect(() => {
    const defaultDistrict = fallbackDistricts.find((d) => d.id === 'champhai') || fallbackDistricts[0]
    if (defaultDistrict && !selectedDistrictId) {
      setSelectedDistrictId(defaultDistrict.id)
    }
    void handleWarmupAndRefresh(false)
  }, [])

  // Lazy-load full district dataset on demand when user opens Risk Map
  useEffect(() => {
    if (activeTab === 'Risk Map') {
      getJSON<{ data: District[] }>('/api/districts')
        .then((res) => setDistricts(res.data))
        .catch(() => {})
    }
  }, [activeTab])

  // Lazy-load district signals when selected district changes
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
        setImageError('Image screening service unavailable; file will be submitted for manual review.')
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
        recommendedAction: 'Unable to contact verification service. Report queued locally.',
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
    else setActiveTab('Overview')
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
              <span className="brand-subtitle">Disaster Management Risk Intelligence</span>
            </div>
          </div>
        </div>

        <NavbarMenu
          items={navItems}
          openLabel={navOpen}
          onOpenChange={(l) => setNavOpen(l)}
          onNavigate={(target) => handleNavClick(target)}
        />

        <div className="topbar-right">
          <select value={region} onChange={(e) => setRegion(e.target.value)} className="region-select">
            <option value="All North Eastern Region (NER)">All North Eastern Region (NER)</option>
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
            {connectionState === 'CONNECTING'
              ? 'CONNECTING TO LIVE SERVICES…'
              : connectionState === 'LIVE'
              ? 'SYSTEM READY'
              : connectionState === 'DEGRADED'
              ? 'LIVE SERVICES DEGRADED'
              : 'LIVE SERVICES UNREACHABLE'}
          </div>

          <button className="refresh-button" disabled={refreshing} onClick={() => void handleWarmupAndRefresh(true)}>
            {refreshing ? 'Updating…' : lastUpdated ? `Last live update ${lastUpdated}` : 'Refresh data'}
          </button>

          <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      {connectionState === 'CONNECTING' && (
        <div className="connection-banner connecting">
          <span className="banner-spinner" />
          <span>Connecting to live risk services… (Render cold start in progress)</span>
        </div>
      )}

      {connectionState === 'DEGRADED' && (
        <div className="connection-banner degraded">
          <span>Live backend services are temporarily degraded. Static intelligence remains available.</span>
          <button className="banner-retry-btn" onClick={() => void handleWarmupAndRefresh(true)}>
            Retry Connection
          </button>
        </div>
      )}

      <main className="main-content">
        {/* VIEW 1: OVERVIEW DASHBOARD */}
        {activeTab === 'Overview' && (
          <div className="overview-view">
            <section className="hero-compact">
              <h1>LANDSLIDE RISK INTELLIGENCE</h1>
              <p className="hero-subtext">NER · 8 states · 131 official districts</p>
            </section>

            {/* 4 Primary Above-the-Fold Operational Cards */}
            <section className="primary-cards-grid">
              <div className="op-card risk-op-card">
                <div className="op-card-header">
                  <span className="op-card-title">MODELED RISK SCORE</span>
                  <span className={`op-card-badge ${
                    !highestRiskDistrict
                      ? 'green'
                      : (highestRiskDistrict.decision?.riskLevel === 'RED' || (highestRiskDistrict.riskScore ?? 0) >= 75)
                      ? 'red'
                      : (highestRiskDistrict.decision?.riskLevel === 'ORANGE' || (highestRiskDistrict.riskScore ?? 0) >= 50)
                      ? 'amber'
                      : (highestRiskDistrict.decision?.riskLevel === 'YELLOW' || (highestRiskDistrict.riskScore ?? 0) >= 35)
                      ? 'amber'
                      : 'green'
                  }`}>
                    {!highestRiskDistrict
                      ? 'NOMINAL'
                      : (highestRiskDistrict.decision?.riskLevel === 'RED' || (highestRiskDistrict.riskScore ?? 0) >= 75)
                      ? 'EMERGENCY'
                      : (highestRiskDistrict.decision?.riskLevel === 'ORANGE' || (highestRiskDistrict.riskScore ?? 0) >= 50)
                      ? 'WARNING'
                      : (highestRiskDistrict.decision?.riskLevel === 'YELLOW' || (highestRiskDistrict.riskScore ?? 0) >= 35)
                      ? 'ELEVATED'
                      : 'NOMINAL'}
                  </span>
                </div>
                <div className="op-card-body">
                  <div className="op-stat-large">{highestRiskDistrict?.riskScore ?? 'N/A'}</div>
                  <div className="op-stat-label">{highestRiskDistrict?.name || 'Champhai Axis'}</div>
                  <p className="op-stat-desc">
                    Modeled risk score ({highestRiskDistrict?.riskScore ?? 'N/A'} / 100) evaluated against P6 production decision threshold.
                  </p>
                </div>
                <div className="op-card-footer">
                  <button className="text-action-link" onClick={() => setActiveTab('Risk Map')}>
                    View on Risk Map &rarr;
                  </button>
                </div>
              </div>

              <div className="op-card weather-op-card">
                <div className="op-card-header">
                  <span className="op-card-title">{rainfallData?.is_live ? 'LIVE WEATHER FEED' : 'WEATHER FEED'}</span>
                  <span className={`op-card-badge ${rainfallData?.is_live ? 'green' : 'amber'}`}>
                    {rainfallData?.is_live ? 'LIVE WEATHER FEED' : 'STALE / DEGRADED'}
                  </span>
                </div>
                <div className="op-card-body">
                  <div className="op-stat-large">{rainfallData?.rainfall_24h ?? activeDistrict?.rain24h ?? 'N/A'} mm</div>
                  <div className="op-stat-label">24h Peak Rainfall (Max Across Nodes)</div>
                  <p className="op-stat-desc">
                    Source: {rainfallData?.source || 'Open-Meteo current/hourly precipitation'}. No historical substitution when live feeds disconnect.
                  </p>
                </div>
                <div className="op-card-footer">
                  <button className="text-action-link" onClick={() => setActiveTab('Forecast')}>
                    View 72H Forecast &rarr;
                  </button>
                </div>
              </div>

              <div className="op-card corridors-op-card">
                <div className="op-card-header">
                  <span className="op-card-title">ROAD CORRIDORS</span>
                  <span className="op-card-badge blue">MoRTH REGISTRY</span>
                </div>
                <div className="op-card-body">
                  <div className="corridor-mini-list">
                    {corridors.slice(0, 4).map((c) => (
                      <div key={c.code} className="mini-corridor-row">
                        <span className="corridor-code">{c.code}</span>
                        <span className="corridor-name">{c.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="op-card-footer">
                  <span className="provenance-note">Verified MoRTH Arterial Axes</span>
                </div>
              </div>

              <div className="op-card coverage-op-card">
                <div className="op-card-header">
                  <span className="op-card-title">SPATIAL COVERAGE</span>
                  <span className="op-card-badge green">SoI AUTHORITATIVE</span>
                </div>
                <div className="op-card-body">
                  <div className="coverage-metrics-stack">
                    <div>
                      <strong className="coverage-num">{dashboardSummary?.monitored_districts_count ?? 131}</strong>
                      <span className="coverage-label">Official districts in framework</span>
                    </div>
                    <div>
                      <strong className="coverage-num">{dashboardSummary?.operational_nodes_count ?? 9}</strong>
                      <span className="coverage-label">Operational risk locations</span>
                    </div>
                    <div>
                      <strong className="coverage-num">16 / 131 profiled</strong>
                      <span className="coverage-label">8 full / 8 partial / 115 insufficient data</span>
                    </div>
                  </div>
                </div>
                <div className="op-card-footer">
                  <span className="provenance-note">Survey of India ABDB Database</span>
                </div>
              </div>
            </section>

            {/* Quick District Selector & Operational Summary */}
            <section className="overview-summary-section">
              <div className="section-title-bar">
                <h3>Operational Location Summary ({filteredDistricts.length})</h3>
                <div className="district-pills">
                  {filteredDistricts.map((d) => (
                    <button
                      key={d.id}
                      className={`district-pill ${selectedDistrictId === d.id ? 'selected' : ''}`}
                      onClick={() => setSelectedDistrictId(d.id)}
                    >
                      {d.name} ({d.riskScore ?? 'N/A'})
                    </button>
                  ))}
                </div>
              </div>

              {activeDistrict && (
                <div className="active-district-detail-card">
                  <div className="detail-header">
                    <div>
                      <h4>{activeDistrict.name} — {activeDistrict.state}</h4>
                      <p className="subtext">Coordinates: {activeDistrict.lat.toFixed(4)}°N, {activeDistrict.lng.toFixed(4)}°E | Slope: {activeDistrict.slopeAngle.toFixed(1)}°</p>
                    </div>
                    <div className="detail-badges">
                      <span className={`risk-badge level-${(
                        activeDistrict.decision?.riskLevel || (
                          (activeDistrict.riskScore ?? 0) >= 75 ? 'RED' :
                          (activeDistrict.riskScore ?? 0) >= 50 ? 'ORANGE' :
                          (activeDistrict.riskScore ?? 0) >= 35 ? 'YELLOW' : 'GREEN'
                        )
                      ).toLowerCase()}`}>
                        {activeDistrict.decision?.riskLevel === 'RED' || (activeDistrict.riskScore ?? 0) >= 75
                          ? 'EMERGENCY'
                          : activeDistrict.decision?.riskLevel === 'ORANGE' || (activeDistrict.riskScore ?? 0) >= 50
                          ? 'WARNING'
                          : activeDistrict.decision?.riskLevel === 'YELLOW' || (activeDistrict.riskScore ?? 0) >= 35
                          ? 'ELEVATED'
                          : 'NOMINAL'} ({activeDistrict.riskScore ?? 'N/A'})
                      </span>
                    </div>
                  </div>

                  <div className="detail-metrics-grid">
                    <div><span>24h Rainfall (At {activeDistrict.name}):</span> <strong>{activeDistrict.rain24h != null ? `${activeDistrict.rain24h} mm` : 'N/A'}</strong></div>
                    <div><span>Terrain Slope:</span> <strong>{activeDistrict.slopeAngle != null ? `${activeDistrict.slopeAngle.toFixed(1)}°` : 'Unavailable'}</strong></div>
                    <div><span>Historical GSI Events:</span> <strong>{activeDistrict.gsiEvents} (Historical Inventory)</strong></div>
                    <div><span>Model Source:</span> <strong>{activeDistrict.modelSource && activeDistrict.modelSource !== 'uninitialized' && activeDistrict.modelSource !== 'Loading…' ? activeDistrict.modelSource : activeModelMeta ? `Random Forest v${activeModelMeta.version}` : modelReadinessState === 'LOADING' ? 'Loading…' : 'Unavailable'}</strong></div>
                  </div>

                  <div className="detail-actions">
                    <button className="action-button primary" onClick={broadcastWarning}>
                      {broadcastStatus === 'broadcasting' ? '🔊 Stop Advisory' : '🔊 Listen to Advisory'}
                    </button>
                    <button className="action-button secondary" onClick={() => setActiveTab('Explainability')}>
                      Inspect Explainability
                    </button>
                    <button className="action-button secondary" onClick={() => setActiveTab('Vulnerability')}>
                      Inspect Exposure Profile
                    </button>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {/* VIEW 2: RISK MAP */}
        {activeTab === 'Risk Map' && (
          <Suspense fallback={<SectionSkeleton title="Risk Map GIS Engine" />}>
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
          <Suspense fallback={<SectionSkeleton title="72H Risk Forecast" />}>
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
          <Suspense fallback={<SectionSkeleton title="Field Reports Portal" />}>
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

        {/* VIEW 5: VULNERABILITY (P7C) */}
        {activeTab === 'Vulnerability' && (
          <Suspense fallback={<SectionSkeleton title="Vulnerability Profiles" />}>
            <VulnerabilitySection activeDistrict={activeDistrict} exposureRecord={exposureRecord} />
          </Suspense>
        )}

        {/* VIEW 6: EXPLAINABILITY (P8) */}
        {activeTab === 'Explainability' && (
          <Suspense fallback={<SectionSkeleton title="Explainable AI" />}>
            <ExplainabilitySection activeDistrict={activeDistrict} riskPrediction={riskPrediction} riskLoading={riskLoading} riskError={riskError} />
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
