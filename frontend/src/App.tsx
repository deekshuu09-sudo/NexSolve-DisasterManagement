import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { NavbarMenu } from './components/NavbarMenu'
import { API, fallbackCorridors, fallbackDistricts, getJSON, postJSON } from './lib/api'
import type { District, ForecastPoint, ImageAnalysis, RainfallData, RiskPrediction } from './lib/api'
import './App.css'
import './interactions.css'

type Theme = 'light' | 'dark'
type Corridor = { code: string; name: string; status: string; eta: string }

function FitDistrictBounds({ districts }: { districts: District[] }) {
  const map = useMap()
  useEffect(() => {
    if (districts.length) {
      map.fitBounds(districts.map((district) => [district.lat, district.lng] as [number, number]), { padding: [24, 24] })
    }
  }, [districts, map])
  return null
}
const steps = ['Overview', 'GIS Intelligence', 'Explainable AI', '72H Forecast', 'Field Intelligence', 'Threat Intel', 'Response Matrix', 'Road Corridors']
const sectionIds = ['overview-step', 'map-step', 'xai-step', 'forecast-step', 'field-step', 'alerts-step', 'response-step', 'roads-step']
const navItems = [
  { label: 'DASHBOARD', target: 'overview-step' },
  { label: 'ANALYZE', target: 'map-step', menu: [
    { title: 'Interactive GIS Map', description: 'Operational terrain, hazards & corridors', target: 'map-step' },
    { title: 'Explainable AI (XAI) Engine', description: 'Model factor decomposition & risk explanation', target: 'xai-step' },
  ] },
  { label: 'INTELLIGENCE', target: 'forecast-step', menu: [
    { title: '72H Forecast', description: 'Time-based risk projection interface', target: 'forecast-step' },
    { title: 'Field Intelligence', description: 'Verified ground incident reports', target: 'field-step' },
  ] },
  { label: 'THREAT INTEL', target: 'alerts-step', menu: [
    { title: 'Priority Alerts', description: 'Early warning broadcast queue', target: 'alerts-step' },
    { title: 'Response Matrix', description: 'Emergency response recommendation', target: 'response-step' },
  ] },
  { label: 'SYSTEM', target: 'roads-step', menu: [
    { title: 'Road Corridors', description: 'Infrastructure monitoring status', target: 'roads-step' },
  ] },
]
function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const [workflowOpen, setWorkflowOpen] = useState(false)
  const [workflowVisible, setWorkflowVisible] = useState(true)
  const [navOpen, setNavOpen] = useState<string | null>(null)
  const [activeStep, setActiveStep] = useState(0)
  const [region, setRegion] = useState('All North Eastern Region (NER)')
  const [layer, setLayer] = useState('All Layers')
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null)
  const [districts, setDistricts] = useState<District[]>(fallbackDistricts)
  const [corridors, setCorridors] = useState<Corridor[]>(fallbackCorridors)
  const [apiOnline, setApiOnline] = useState(false)
  const [loading, setLoading] = useState(true)
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
  const [forecast, setForecast] = useState<ForecastPoint[]>([])
  const [forecastSource, setForecastSource] = useState('')
  const [forecastLive, setForecastLive] = useState(false)
  const [forecastLoading, setForecastLoading] = useState(false)
  const [forecastError, setForecastError] = useState<string | null>(null)
  const [rainfallData, setRainfallData] = useState<RainfallData | null>(null)
  const [broadcastStatus, setBroadcastStatus] = useState<'idle' | 'broadcasting' | 'complete' | 'unavailable'>('idle')

  const requestRiskPrediction = async (district: District) => {
    if (district.rainfall_3d == null || district.rainfall_7d == null) {
      setRiskPrediction(null)
      setRiskError('Risk prediction inputs are unavailable from the district feed.')
      return
    }

    setRiskLoading(true)
    setRiskError(null)

    try {
      const response = await postJSON<{data: RiskPrediction}>('/api/risk', {
        latitude: district.lat,
        longitude: district.lng,
        rainfall_1d: district.rain24h,
        rainfall_3d: district.rainfall_3d,
        rainfall_7d: district.rainfall_7d,
        date: new Date().toISOString().slice(0, 10),
      })
      setRiskPrediction(response.data)
      // Merge live risk prediction into the selected district so all sections use canonical current risk
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
              }
            : d
        )
      )
    } catch (error) {
      console.error(error)
      setRiskPrediction(null)
      setRiskError('Live risk prediction unavailable; showing the district feed result.')
    } finally {
      setRiskLoading(false)
    }
  }

  const loadDistrictSignals = async (district: District) => {
    setForecastLoading(true)
    const [riskResponse, rainfallResponse, forecastResponse] = await Promise.allSettled([
      requestRiskPrediction(district),
      getJSON<RainfallData>(`/api/rainfall/current?latitude=${district.lat}&longitude=${district.lng}`),
      getJSON<{forecast: ForecastPoint[]; source: string; is_live: boolean}>(`/api/forecast/${district.id}`),
    ])
    if (rainfallResponse.status === 'fulfilled') setRainfallData(rainfallResponse.value)
    if (forecastResponse.status === 'fulfilled') {
      setForecast(forecastResponse.value.forecast)
      setForecastSource(forecastResponse.value.source)
      setForecastLive(forecastResponse.value.is_live)
      setForecastError(forecastResponse.value.is_live ? null : 'Forecast source unavailable — showing latest available IMD data.')
    } else {
      setForecast([])
      setForecastError('Forecast source unavailable — showing latest available IMD data.')
    }
    if (riskResponse.status === 'fulfilled') setApiOnline(true)
    setForecastLoading(false)
  }

  const broadcastWarning = () => {
    if (!('speechSynthesis' in window)) {
      setBroadcastStatus('unavailable')
      return
    }

    window.speechSynthesis.cancel()
    const districtName = activeDistrict?.name || 'the monitored area'
    const warningMessages = [
      { lang: 'en-IN', text: `Emergency warning for ${districtName}. Landslide risk is elevated. Avoid travel through affected corridors and follow local authority instructions.` },
      { lang: 'hi-IN', text: `${districtName} के लिए आपातकालीन चेतावनी। भूस्खलन का खतरा बढ़ गया है। प्रभावित मार्गों पर यात्रा न करें और स्थानीय अधिकारियों के निर्देशों का पालन करें।` },
      { lang: 'as-IN', text: `${districtName} ৰ বাবে জৰুৰী সতৰ্কবাণী। ভূমিস্খলনৰ আশংকা বৃদ্ধি পাইছে। প্ৰভাৱিত পথত যাত্ৰা নকৰিব আৰু স্থানীয় কৰ্তৃপক্ষৰ নিৰ্দেশনা পালন কৰক।` },
    ]
    let remaining = warningMessages.length
    setBroadcastStatus('broadcasting')
    warningMessages.forEach(({ lang, text }) => {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = lang
      utterance.rate = 0.9
      utterance.onend = () => {
        remaining -= 1
        if (remaining === 0) setBroadcastStatus('complete')
      }
      utterance.onerror = () => setBroadcastStatus('unavailable')
      window.speechSynthesis.speak(utterance)
    })
  }

  const getResponseRecommendation = (riskScore: number | undefined, status: string | undefined) => {
    if (riskScore === undefined || status === undefined) {
      return {
        title: 'Emergency Response Action',
        heading: 'Response Planning Required',
        description: 'Risk data unavailable. Unable to determine response recommendation.',
      }
    }
    if (riskScore >= 80) {
      return {
        title: 'Critical Emergency Response',
        heading: 'Pre-position NDRF / SDRF Battalion Unit',
        description: 'IMMEDIATE: Pre-position emergency response teams. Activate district emergency operations center. Issue public early warning broadcast. Prepare evacuation corridors.',
      }
    }
    if (riskScore >= 60) {
      return {
        title: 'High Alert Response',
        heading: 'Pre-position Response Teams & Resources',
        description: 'HEIGHTENED ALERT: Pre-position emergency response teams and resources. Enhance monitoring and communication. Prepare contingency corridors for evacuation.',
      }
    }
    if (riskScore >= 40) {
      return {
        title: 'Moderate Monitoring Response',
        heading: 'Increase Monitoring & Targeted Inspection',
        description: 'INCREASED MONITORING: Conduct targeted field inspection. Enhance monitoring systems. Maintain team readiness. Review evacuation procedures.',
      }
    }
    return {
      title: 'Routine Monitoring',
      heading: 'Standard Preparedness & Monitoring',
      description: 'ROUTINE: Maintain standard monitoring protocols. Regular preparedness drills. Community awareness updates.',
    }
  }

  const refresh = async () => {
    setLoading(true)
    try {
      const [districtResponse, corridorResponse] = await Promise.all([
        getJSON<{data: District[]}>('/api/districts'),
        getJSON<{data: Corridor[]}>('/api/corridors'),
      ])
      setDistricts(districtResponse.data)
      setCorridors(corridorResponse.data)
      setApiOnline(true)
      const focusDistrict = districtResponse.data.find((district) => district.id === selectedDistrictId) || districtResponse.data.find((district) => district.id === 'champhai') || districtResponse.data[0]
      if (focusDistrict) {
        setSelectedDistrictId(focusDistrict.id)
        await loadDistrictSignals(focusDistrict)
      }
    } catch {
      setApiOnline(false)
      setForecastLoading(false)
      setForecast([])
      setForecastSource('Backend unavailable')
      setForecastError('Forecast unavailable — start the FastAPI backend on port 8000.')
      setRainfallData(null)
      setRiskPrediction(null)
      setRiskError('Live risk prediction unavailable; showing the district feed result.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => { refresh() }, [])

  useEffect(() => {
    const selected = districts.find((district) => district.id === selectedDistrictId)
    if (selected) void loadDistrictSignals(selected)
  }, [selectedDistrictId])

  const submitReport = async () => {
    if (!reportLocation.trim() || !reportDescription.trim()) {
      return
    }

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

      if (!response.ok) {
        throw new Error(`Report API ${response.status}`)
      }

      const result = await response.json()
      setReportResult(result.report)
      setSubmittedReports((current) => [result.report, ...current.filter((report) => report.id !== result.report.id)])
    } catch (error) {
      console.error(error)

      setReportResult({
        verified: false,
        verificationStatus: 'ERROR',
        verificationConfidence: 0,
        severity: 'Unknown',
        recommendedAction: 'Unable to contact the verification service.',
      })
    } finally {
      setReportSubmitting(false)
    }
  }

  const analyzeReportImage = async () => {
    if (!reportImage) return
    setImageLoading(true)
    setImageError(null)
    try {
      const body = new FormData()
      body.append('file', reportImage)
      body.append('description', reportDescription)
      const response = await fetch(`${API}/api/reports/analyze-image`, { method: 'POST', body })
      if (!response.ok) throw new Error(`API ${response.status}`)
      setImageAnalysis(await response.json())
    } catch (error) {
      console.error(error)
      setImageAnalysis(null)
      setImageError('Image analysis unavailable. Continue with manual incident details.')
    } finally {
      setImageLoading(false)
    }
  }

  const navigateTo = (id: string) => {
    const normalizedId = sectionIds.includes(id)
      ? id
      : id === 'xai'
        ? 'xai-step'
        : id === 'field'
          ? 'field-step'
          : id
    const index = sectionIds.indexOf(normalizedId)
    if (index >= 0) setActiveStep(index)
    setNavOpen(null)
    setWorkflowOpen(false)
    window.history.replaceState(null, '', `#${normalizedId}`)
    document.getElementById(normalizedId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  useEffect(() => {
    const syncHash = () => {
      const id = window.location.hash.slice(1)
      const index = sectionIds.indexOf(id)
      if (index >= 0) {
        setActiveStep(index)
        window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: 'start' }), 0)
      }
    }
    syncHash()
    window.addEventListener('hashchange', syncHash)
    return () => window.removeEventListener('hashchange', syncHash)
  }, [])

  useEffect(() => {
    let frame = 0

    const syncStepToScroll = () => {
      if (frame) return
      frame = window.requestAnimationFrame(() => {
        frame = 0
        const readingLine = Math.min(window.innerHeight * 0.32, 300)
        const sections = sectionIds
          .map((id, index) => ({ element: document.getElementById(id), index }))
          .filter((item): item is { element: HTMLElement; index: number } => Boolean(item.element))
        const visibleSection = sections.reduce<{ element: HTMLElement; index: number } | null>((current, item) => {
          if (item.element.getBoundingClientRect().top <= readingLine) return item
          return current
        }, null)
        const nextStep = visibleSection?.index ?? sections[0]?.index ?? 0
        setActiveStep((current) => {
          if (current === nextStep) return current
          const nextHash = `#${sectionIds[nextStep]}`
          if (window.location.hash !== nextHash) window.history.replaceState(null, '', nextHash)
          return nextStep
        })
      })
    }

    syncStepToScroll()
    window.addEventListener('scroll', syncStepToScroll, { passive: true })
    window.addEventListener('resize', syncStepToScroll)
    return () => {
      window.removeEventListener('scroll', syncStepToScroll)
      window.removeEventListener('resize', syncStepToScroll)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [])

  const filteredDistricts = useMemo(() => {
    if (!region || region === 'All North Eastern Region (NER)') return districts
    return districts.filter((d) => d.state.toLowerCase() === region.toLowerCase())
  }, [districts, region])

  useEffect(() => {
    if (filteredDistricts.length > 0 && !filteredDistricts.some((d) => d.id === selectedDistrictId)) {
      setSelectedDistrictId(filteredDistricts[0].id)
    }
  }, [filteredDistricts, selectedDistrictId])

  const criticalCount = filteredDistricts.filter(d => d.riskScore != null && d.riskScore >= 80).length
  const highCount = filteredDistricts.filter(d => d.riskScore != null && d.riskScore >= 60 && d.riskScore < 80).length
  const avgRainDisplay = useMemo(() => {
    const valid = filteredDistricts.filter(d => d.rain24h != null && !isNaN(d.rain24h))
    if (!valid.length) return 'N/A'
    const total = valid.reduce((sum, item) => sum + (item.rain24h ?? 0), 0)
    return total === 0 ? 'N/A' : `${Math.round(total / valid.length)} mm`
  }, [filteredDistricts])
  const activeDistrict = districts.find(d => d.id === selectedDistrictId) || filteredDistricts[0] || districts[0]
  const factorData = riskPrediction?.factors?.length ? riskPrediction.factors : activeDistrict?.factors?.length ? activeDistrict.factors : [
    { name: 'Rainfall Intensity & Accumulation', weight: 40, impact: Math.min((activeDistrict?.rain24h ?? 0) / 2, 100) },
    { name: 'Soil Moisture Saturation', weight: 25, impact: activeDistrict?.soilSat ?? 0 },
    { name: 'Terrain Slope & DEM Cut Angle', weight: 20, impact: Math.min((activeDistrict?.slopeAngle ?? 0) / 45 * 100, 100) },
    { name: 'GSI Historical Inventory', weight: 15, impact: Math.min((activeDistrict?.gsiEvents ?? 0) / 20 * 100, 100) },
  ]
  const peakForecast = forecast.reduce<ForecastPoint | null>((peak, point) => !peak || point.riskScore > peak.riskScore ? point : peak, null)
  const chartForecast = forecast.filter((_, index) => index % 6 === 0).slice(0, 12)
  const forecastWindows = [
    { label: 'NEXT 24H', points: forecast.slice(0, 24) },
    { label: '24–48H', points: forecast.slice(24, 48) },
    { label: '48–72H', points: forecast.slice(48, 72) },
  ].map((window) => ({
    ...window,
    rainfall: window.points.reduce((sum, point) => sum + point.rainfall, 0),
    peak: window.points.reduce<ForecastPoint | null>((peak, point) => !peak || point.riskScore > peak.riskScore ? point : peak, null),
  }))
  const showDistrictMarkers = layer === 'All Layers' || layer === 'Risk Heatmap' || layer === 'Rainfall Intensity'
  const showCorridorStatus = layer === 'All Layers' || layer === 'Road Corridors'
  const layerNotice = layer === 'Relief Shelters'
    ? 'Relief shelter coordinates are not available in the corridor API.'
    : layer === 'SAR Vectors'
      ? 'SAR vector data is not available from the connected backend.'
      : layer === 'Rainfall Intensity'
        ? 'Rainfall intensity overlay derived from the current district rainfall feed; no radar tile source is configured.'
        : null

  return (
    <div className={`app-shell ${workflowVisible ? '' : 'workflow-hidden'}`}>
      {reportOpen && (
        <div className="report-overlay">
          <div className="report-modal">
            <div className="report-modal-header">
              <div>
                <small className="kicker">FIELD INTELLIGENCE</small>
                <h2>Log Field Incident</h2>
              </div>

              <button
                type="button"
                className="report-close"
                onClick={() => {
                  setReportOpen(false)
                  setReportResult(null)
                      setReportImage(null)
                      setReportImagePreview(null)
                  setImageAnalysis(null)
                  setImageError(null)
                }}
              >
                ×
              </button>
            </div>

            {!reportResult ? (
              <>
                <p className="report-intro">
                  Submit a ground observation for AI-assisted verification.
                </p>

                <label className="report-label">
                  LOCATION
                  <input
                    value={reportLocation}
                    onChange={(event) => setReportLocation(event.target.value)}
                    placeholder="e.g. Champhai, Mizoram"
                  />
                </label>

                <div className="report-coordinate-grid">
                  <label className="report-label">
                    LATITUDE
                    <input value={reportLatitude} onChange={(event) => setReportLatitude(event.target.value)} inputMode="decimal" placeholder="e.g. 23.4756" />
                  </label>
                  <label className="report-label">
                    LONGITUDE
                    <input value={reportLongitude} onChange={(event) => setReportLongitude(event.target.value)} inputMode="decimal" placeholder="e.g. 93.3289" />
                  </label>
                </div>

                <label className="report-label">
                  INCIDENT DESCRIPTION
                  <textarea
                    value={reportDescription}
                    onChange={(event) => setReportDescription(event.target.value)}
                    placeholder="Describe the landslide, debris, road blockage or slope failure..."
                    rows={5}
                  />
                </label>

                <label className="report-label">
                  INCIDENT IMAGE (OPTIONAL)
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null
                      setReportImage(file)
                      setReportImagePreview(file ? URL.createObjectURL(file) : null)
                      setImageAnalysis(null)
                      setImageError(null)
                    }}
                  />
                </label>

                {reportImagePreview && <img className="report-image-preview" src={reportImagePreview} alt="Selected incident preview" />}

                <button type="button" className="secondary-button" disabled={!reportImage || imageLoading} onClick={analyzeReportImage}>
                  {imageLoading ? '◌ ANALYZING IMAGE...' : 'ANALYZE IMAGE'}
                </button>

                {imageAnalysis && (
                  <div className="report-image-result">
                    <strong>{imageAnalysis.verificationMode}</strong>
                    <span>Image quality: {imageAnalysis.imageQuality} · screening confidence {imageAnalysis.verificationConfidence}%</span>
                    <span>Text match: {imageAnalysis.descriptionMatch ? 'YES' : 'NO'}</span>
                    <span>Indicators: {imageAnalysis.visualIndicators.join(', ') || 'none detected'}</span>
                    <small>{imageAnalysis.recommendedAction}</small>
                    <small>Model source: {imageAnalysis.modelSource}</small>
                  </div>
                )}
                {imageError && <small className="risk-error">{imageError}</small>}

                <button
                  type="button"
                  className="primary-button report-submit"
                  disabled={reportSubmitting || !reportLocation.trim() || !reportDescription.trim()}
                  onClick={submitReport}
                >
                  {reportSubmitting ? '◌ VERIFYING INCIDENT...' : '✓ SUBMIT FOR AI VERIFICATION'}
                </button>
              </>
            ) : (
              <div className="report-result">
                <div className="report-result-status">
                  <span className="report-result-icon">{reportResult.verified ? '✓' : '!'}</span>

                  <div>
                    <small>FIELD INCIDENT RESULT</small>
                    <strong>{reportResult.verificationStatus}</strong>
                  </div>
                </div>

                <div className="report-result-grid">
                  <article>
                    <small>IMAGE</small>
                    <strong>{reportResult.imageAnalysis?.imageAccepted ? 'RECEIVED' : 'NOT PROVIDED'}</strong>
                  </article>
                  <article>
                    <small>IMAGE QUALITY</small>
                    <strong>{reportResult.imageAnalysis?.imageQuality || 'N/A'}</strong>
                  </article>
                  <article>
                    <small>LOCATION</small>
                    <strong>{reportResult.latitude != null || reportResult.longitude != null ? 'RECEIVED' : 'TEXT ONLY'}</strong>
                  </article>
                  <article>
                    <small>DESCRIPTION</small>
                    <strong>ANALYSED</strong>
                  </article>
                  <article>
                    <small>CONFIDENCE</small>
                    <strong>{reportResult.verificationConfidence}%</strong>
                  </article>

                  <article>
                    <small>SEVERITY</small>
                    <strong>{reportResult.severity}</strong>
                  </article>
                </div>

                <div className="report-result-action">
                  <small>RECOMMENDED RESPONSE</small>
                  <p>{reportResult.recommendedAction}</p>
                </div>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setReportOpen(false)
                    setReportResult(null)
                    setReportLocation('')
                    setReportLatitude('')
                    setReportLongitude('')
                    setReportDescription('')
                    setReportImage(null)
                    setReportImagePreview(null)
                    setImageAnalysis(null)
                    setImageError(null)
                    navigateTo('field')
                  }}
                >
                  View Field Intelligence →
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      <header className="topbar">
        <a className="brand" href="#overview-step" onClick={(event) => { event.preventDefault(); navigateTo('overview-step') }}>
          <span className="brand-mark">N</span>
          <b>NEXSOLVE</b>
        </a>
        <NavbarMenu items={navItems} openLabel={navOpen} onOpenChange={setNavOpen} onNavigate={navigateTo} />
        <div className="topbar-tools">
          <select value={region} onChange={(event) => setRegion(event.target.value)} aria-label="Select monitoring region">
            <option>All North Eastern Region (NER)</option>
            <option>Mizoram</option>
            <option>Manipur</option>
            <option>Meghalaya</option>
            <option>Assam</option>
            <option>Arunachal Pradesh</option>
            <option>Nagaland</option>
            <option>Tripura</option>
            <option>Sikkim</option>
          </select>
          <span className="system-status"><i /> {apiOnline ? 'SYSTEM READY' : 'OFFLINE FALLBACK'}</span>
          <button className="icon-button" aria-label="Toggle color theme" onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}>{theme === 'dark' ? '☀' : '☾'}</button>
          <button className="icon-button" onClick={refresh} aria-label="Refresh risk model" disabled={loading}>↻</button>
        </div>
      </header>

      {!workflowVisible && <button className="workflow-fab" onClick={() => setWorkflowVisible(true)} aria-label="Open workflow">☰ <span>WORKFLOW</span></button>}
      <div className={`backdrop ${workflowOpen ? 'visible' : ''}`} onClick={() => setWorkflowOpen(false)} />

      <div className="workspace">
        <aside className={`sidebar ${workflowOpen ? 'open' : ''} ${workflowVisible ? '' : 'closed'}`}>
          <div className="sidebar-heading">
            <b>WORKFLOW</b>
            <button onClick={() => setWorkflowVisible(false)} aria-label="Close workflow">×</button>
          </div>

          <nav className="steps">
            {steps.map((step, index) => (
              <button key={step} className={activeStep === index ? 'active' : ''} onClick={() => navigateTo(sectionIds[index])}>
                <em>{['OVERVIEW', 'GIS INTELLIGENCE', 'EXPLAINABLE AI', '72H FORECAST', 'FIELD INTELLIGENCE', 'THREAT INTEL', 'RESPONSE MATRIX', 'ROAD CORRIDORS'][index]}</em>
                <strong>{String(index + 1).padStart(2, '0')}</strong>
                <span>
                  <b>{step}</b>
                  <small>{['Regional hazard metrics & overview', 'Terrain analysis & GIS intelligence', 'Risk decomposition & factor analysis', '72-hour risk forecast & projection', 'Crowdsourced incidents & AI verification', 'Priority alerts & early warning broadcast', 'Emergency response recommendations', 'Infrastructure monitoring status'][index]}</small>
                </span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="content">
          <section id="overview-step">
            <small className="kicker">01 / OVERVIEW</small>
            <h1>Predict Landslides.<br /><em>Save Lives &amp; Roads.</em></h1>
            <p className="lede">Enterprise real-time GIS monitoring and hazard forecasting platform for the 8 North Eastern States of India.</p>
            <button className="primary-button" onClick={() => { setReportOpen(true); setReportResult(null) }}>＋ Log Field Incident</button>
            <div className="panel metrics-panel">
              <small className="kicker">HAZARD METRICS SUMMARY</small>
              <div className="metrics">
                {[['Critical Risk Zones', String(criticalCount).padStart(2,'0'), 'Risk score ≥ 80', 'critical'], ['High Risk Zones', String(highCount).padStart(2,'0'), 'Risk score 60–79', 'warning'], ['Avg 24h Rainfall', avgRainDisplay, 'From API district feed', 'neutral'], ['Road Corridors Under Watch', String(corridors.length).padStart(2,'0'), `${corridors.filter(c => c.status !== 'OPEN').length} require attention`, 'neutral']].map(([label, value, note, tone]) => (
                  <article className={`metric ${tone}`} key={label as string}>
                    <span className="metric-icon">{tone === 'critical' ? '⚠️' : tone === 'warning' ? '◒' : '◌'}</span>
                    <div>
                      <small>{label as string}</small>
                      <strong>{value as string}</strong>
                      <span>{note as string}</span>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section id="map-step" className="section">
            <small className="kicker">02 / GIS INTELLIGENCE</small>
            <h2>North Eastern Region (NER) Hazard Map</h2>
            <p className="lede">Risk markers are sourced from the backend risk feed and can be filtered by operational layer.</p>
            <div className="panel">
              <div className="panel-head">
                <small className="kicker">TERRAIN &amp; CORRIDOR MAP</small>
                <div className="layer-controls">
                  {['All Layers', 'Risk Heatmap', 'Rainfall Intensity', 'Road Corridors', 'Relief Shelters', 'SAR Vectors'].map((item) => (
                    <button className={layer === item ? 'active' : ''} key={item} onClick={() => setLayer(item)} aria-pressed={layer === item}>{item}</button>
                  ))}
                </div>
              </div>
              <div className={`map-surface layer-${layer.toLowerCase().replaceAll(' ', '-')}`}>
                <MapContainer center={[25.2, 93.5]} zoom={6} scrollWheelZoom className="leaflet-map" aria-label="North Eastern India operational hazard map">
                  <FitDistrictBounds districts={filteredDistricts} />
                  <TileLayer
                    attribution='&copy; OpenStreetMap contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                {showDistrictMarkers && filteredDistricts.map((district) => (
                  <CircleMarker
                    key={district.id}
                    center={[district.lat, district.lng]}
                    pathOptions={{
                      color: layer === 'Rainfall Intensity' ? '#277da1' : (district.riskScore ?? 0) >= 80 ? '#d73c50' : (district.riskScore ?? 0) >= 60 ? '#23a8b8' : (district.riskScore ?? 0) >= 40 ? '#5e63d9' : '#2f9b72',
                      fillColor: layer === 'Rainfall Intensity' ? '#f8961e' : (district.riskScore ?? 0) >= 80 ? '#d73c50' : (district.riskScore ?? 0) >= 60 ? '#23a8b8' : (district.riskScore ?? 0) >= 40 ? '#5e63d9' : '#2f9b72',
                      fillOpacity: layer === 'Rainfall Intensity' ? 0.35 : 0.8,
                      weight: 2,
                    }}
                    radius={layer === 'Rainfall Intensity' ? Math.max(10, Math.min(24, (district.rain24h ?? 0) / 9)) : (district.riskScore ?? 0) >= 80 ? 11 : 8}
                    eventHandlers={{ click: () => { setSelectedDistrictId(district.id); navigateTo('xai-step') } }}
                  >
                    <Popup>
                      <strong>{district.name}</strong><br />
                      State: {district.state}<br />
                      Type: {(district as any).point_type || 'Operational Point'}<br />
                      Risk: {district.riskScore != null ? `${district.riskScore}/100 · ${district.status}` : 'DATA UNAVAILABLE'}<br />
                      24h rainfall: {district.rain24h != null ? `${district.rain24h}mm` : 'N/A'}{layer === 'Rainfall Intensity' ? ' · intensity overlay' : ''}<br />
                      3-day rainfall: {district.rainfall_3d ?? 'N/A'}mm<br />
                      7-day rainfall: {district.rainfall_7d ?? 'N/A'}mm<br />
                      Model source: {district.modelSource}<br />
                      <small style={{ color: '#888' }}>State boundaries: Configured (Survey of India GeoJSON Pending)</small>
                    </Popup>
                  </CircleMarker>
                ))}
                </MapContainer>
                <span className="map-layer-label">{layer} · INTERACTIVE OSM GIS</span>
                {layerNotice && <span className="map-layer-notice">{layerNotice}</span>}
                {selectedDistrictId && <span className="map-selected-label">Selected: {districts.find((district) => district.id === selectedDistrictId)?.name}</span>}
                {showCorridorStatus && <div className="map-corridor-status" aria-label="Corridor status">
                  {corridors.map((corridor) => <span key={corridor.code} className={corridor.status.toLowerCase()}>{corridor.code} · {corridor.status}</span>)}
                </div>}
              </div>
              <div className="map-footer">
                <span><i className="legend red" /> Critical (&gt; 80)　<i className="legend cyan" /> High (60–80)　<i className="legend violet" /> Moderate (40–60)　<i className="legend green" /> Low (&lt; 40)</span>
                <small>8-State Coverage Configured · Survey of India GeoJSON Boundaries Pending Integration · Risk Feed: {apiOnline ? 'Live API' : 'Offline Fallback'}</small>
              </div>
            </div>
          </section>

          <section id="xai-step" className="section">
            <small className="kicker">03 / EXPLAINABLE AI ENGINE</small>
            <h2>Landslide Risk Breakdown: {activeDistrict?.name || 'Selected District'}</h2>
            <div className="panel">
              <div className="panel-head">
                <small className="kicker">FACTOR DECOMPOSITION MATRIX</small>
                <span className="score">PREDICTED RISK SCORE <b>{riskLoading ? 'LOADING' : (riskPrediction?.riskScore ?? activeDistrict?.riskScore) != null ? `${riskPrediction?.riskScore ?? activeDistrict?.riskScore} / 100` : 'N/A (WEATHER FEED OFFLINE)'}</b></span>
              </div>
              <div className="factors">
                {factorData.map((factor) => (
                  <article key={factor.name}>
                    <div>
                      <b>{factor.name}</b>
                      <span>{factor.weight}%</span>
                    </div>
                    <p>{factor.impact >= 80 ? 'Observed conditions exceed operational threshold' : 'Observed conditions within monitored range'}</p>
                    <div className="progress"><i style={{ width: `${factor.impact}%` }} /></div>
                    <small>Impact index {Math.round(factor.impact)} · {riskPrediction?.modelSource ?? activeDistrict?.modelSource}</small>
                  </article>
                ))}
              </div>
              <div className="simulator">
                <b>⚡ Risk engine status:</b>
                <span>{riskPrediction ? `POST /api/risk · ${riskPrediction.status} · confidence ${riskPrediction.confidence}%` : apiOnline ? `District feed connected · confidence ${activeDistrict?.confidence ?? 0}%` : 'Offline fallback active'}</span>
                {riskError && <span className="risk-error">{riskError}</span>}
                <small className="terrain-context-note">
                  Terrain context (elevation, slope, aspect, curvature): Not currently used by the trained Random Forest model. NASADEM files are being downloaded.
                </small>
              </div>
            </div>
          </section>

          <section id="forecast-step" className="section">
            <small className="kicker">04 / 72H FORECAST</small>
            <h2>Predictive Analytics &amp; Risk Projection</h2>
            <div className="panel">
              <div className="panel-head">
                <small className="kicker">{forecastLive ? 'LIVE 72H FORECAST' : 'LATEST AVAILABLE 72H FORECAST'}</small>
                <b>{forecastLoading ? 'Loading forecast...' : peakForecast ? `Peak ${peakForecast.riskScore}/100 · ${peakForecast.status}` : 'Forecast unavailable'}</b>
              </div>
              <div className="forecast-summary">
                <span>Recent rainfall: {rainfallData ? `${rainfallData.rainfall_1d}mm / 24h · ${rainfallData.rainfall_3d}mm / 3d · ${rainfallData.rainfall_7d}mm / 7d` : 'loading'}</span>
                <span>Updated: {rainfallData ? new Date(rainfallData.timestamp).toLocaleString() : 'loading'}</span>
                <span>Peak period: {peakForecast ? new Date(peakForecast.timestamp).toLocaleString() : 'n/a'}</span>
                <span>Source: {forecastSource || 'loading'}</span>
              </div>
              <div className="forecast-windows">
                {forecastWindows.map((window) => <span key={window.label}>{window.label}: {window.points.length ? `${window.rainfall.toFixed(1)}mm · peak ${window.peak?.riskScore}/100 ${window.peak?.status}` : 'unavailable'}</span>)}
              </div>
              {forecastError ? <p className="risk-error">{forecastError}</p> : (
                <div className="forecast-chart" aria-label="72-hour rainfall and risk forecast chart">
                  {chartForecast.map((point) => (
                    <div className="forecast-column" key={point.timestamp} title={`${point.status}: ${point.riskScore}/100 risk, ${point.rainfall}mm rainfall`}>
                      <i style={{ height: `${Math.max(8, point.riskScore)}%` }} />
                      <small>{new Date(point.timestamp).getUTCHours()}h</small>
                    </div>
                  ))}
                </div>
              )}
              <small className="kicker">Risk scores are computed by the trained Random Forest for each rainfall forecast point; the time-indexed source is labeled above.</small>
            </div>
          </section>

          <section id="field-step" className="section">
            <small className="kicker">05 / FIELD INTELLIGENCE</small>
            <h2>Crowdsourced Incident Feed &amp; AI-Assisted Verification</h2>
            <div className="panel list-panel">
              <small className="kicker">VERIFIED GROUND REPORTS</small>
              {submittedReports.map((report) => (
                <article className="list-row" key={report.id}>
                  <span className="verified">{report.verificationStatus === 'AI_ASSISTED_REVIEW' ? 'AI' : 'REVIEW'}</span>
                  <div>
                    <b>{report.location}</b>
                    <small>{report.description} · {report.severity} · confidence {report.verificationConfidence}%</small>
                  </div>
                </article>
              ))}
              {districts.map((district) => (
                <article className="list-row" key={district.id}>
                  <span className="verified">API</span>
                  <div>
                    <b>{district.name}</b>
                    <small>{district.state} · rainfall {district.rain24h}mm · risk score {district.riskScore}/100</small>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section id="alerts-step" className="section">
            <small className="kicker">06 / THREAT INTEL</small>
            <h2>Active Priority Alerts</h2>
            <div className="panel list-panel">
              <small className="kicker">EARLY WARNING BROADCAST LIST</small>
              {districts.filter(d => d.riskScore != null && d.riskScore >= 80).slice(0,3).map((district) => (
                <article className="list-row" key={district.id}>
                  <span className="severity critical">{district.status}</span>
                  <div>
                    <b>{district.name}</b>
                    <small>Backend risk score {district.riskScore}/100 · {district.rain24h ?? 'N/A'}mm rainfall · confidence {district.confidence}%</small>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section id="response-step" className="section">
            <small className="kicker">07 / RESPONSE MATRIX</small>
            <h2>{activeDistrict?.name || 'Selected District'} {getResponseRecommendation(activeDistrict?.riskScore ?? undefined, activeDistrict?.status).title}</h2>
            <div className="panel response">
              <span>🚨</span>
              <div>
                <h3>{getResponseRecommendation(activeDistrict?.riskScore ?? undefined, activeDistrict?.status).heading}</h3>
                <p>Response recommendation is driven by the current {activeDistrict?.name || 'selected district'} risk state: <b>{activeDistrict?.status}</b> ({activeDistrict?.riskScore ?? 'N/A'}/100). {getResponseRecommendation(activeDistrict?.riskScore ?? undefined, activeDistrict?.status).description}</p>
                <button
                  className="primary-button"
                  onClick={broadcastWarning}
                  disabled={broadcastStatus === 'broadcasting' || (activeDistrict?.riskScore ?? 0) < 60}
                  aria-live="polite"
                >
                  📢 {broadcastStatus === 'broadcasting' ? 'Broadcasting Warning...' : 'Broadcast Multilingual Audio Early Warning'}
                </button>
                {broadcastStatus === 'complete' && <small className="broadcast-status success">Warning played in English, Hindi, and Assamese.</small>}
                {broadcastStatus === 'unavailable' && <small className="broadcast-status error">Audio playback is unavailable in this browser.</small>}
                {(activeDistrict?.riskScore ?? 0) < 60 && <small className="broadcast-status neutral">Broadcast available for High/Critical risk levels.</small>}
              </div>
            </div>
          </section>

          <section id="roads-step" className="section">
            <small className="kicker">08 / ROAD CORRIDORS</small>
            <h2>Priority Arterial Highway Corridors</h2>
            <div className="panel roads">
              <small className="kicker">INFRASTRUCTURE MONITORING</small>
              {corridors.map((corridor) => (
                <article key={corridor.code}>
                  <b>{corridor.code} · {corridor.name}</b>
                  <span className={corridor.status.toLowerCase()}>{corridor.status}</span>
                  <small>ETA: {corridor.eta}</small>
                </article>
              ))}
            </div>
          </section>

          <footer>
            <b>NEXSOLVE</b> — Enterprise Landslide &amp; Hazard Intelligence Platform.<br />
            Risk feed is API-backed and powered by a trained Random Forest landslide risk model using GSI event-derived labels and IMD rainfall features.
          </footer>
        </main>
      </div>
    </div>
  )
}

export default App
