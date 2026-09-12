import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { NavbarMenu } from './components/NavbarMenu'
import { API, fallbackCorridors, fallbackDistricts, getJSON, getExposure, postJSON, getDashboardSummary } from './lib/api'
import type { District, ExposureRecord, ForecastPoint, ImageAnalysis, RainfallData, RiskPrediction, DashboardSummary } from './lib/api'
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
    { title: 'Priority Alerts', description: 'Priority alert & decision support queue', target: 'alerts-step' },
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
  const [exposureRecord, setExposureRecord] = useState<ExposureRecord | null>(null)
  const [forecast, setForecast] = useState<ForecastPoint[]>([])
  const [forecastSource, setForecastSource] = useState('')
  const [forecastLive, setForecastLive] = useState(false)
  const [forecastLoading, setForecastLoading] = useState(false)
  const [forecastError, setForecastError] = useState<string | null>(null)
  const [rainfallData, setRainfallData] = useState<RainfallData | null>(null)
  const [broadcastStatus, setBroadcastStatus] = useState<'idle' | 'broadcasting' | 'complete' | 'unavailable'>('idle')
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null)
  const [riskFilter, setRiskFilter] = useState<string>('ALL')
  const [weatherFilter, setWeatherFilter] = useState<string>('ALL')
  const [vulnFilter, setVulnFilter] = useState<string>('ALL')

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
                decision: response.data.decision,
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
    const [riskResponse, rainfallResponse, forecastResponse, exposureResponse] = await Promise.allSettled([
      requestRiskPrediction(district),
      getJSON<RainfallData>(`/api/rainfall/current?latitude=${district.lat}&longitude=${district.lng}`),
      getJSON<{forecast: ForecastPoint[]; source: string; is_live: boolean}>(`/api/forecast/${district.id}`),
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
    if (riskResponse.status === 'fulfilled') setApiOnline(true)
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
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Red, emergency level prototype decision. Escalate to authorized personnel for immediate field verification.`
    } else if (level === 'ORANGE') {
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Orange, warning level. Prepare response resources and verify field conditions.`
    } else if (level === 'YELLOW') {
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Yellow, elevated. Increase monitoring and review local conditions.`
    } else {
      speechText = `NexSolve decision support notice for ${districtName}. Current modeled risk score is ${score} out of 100. Decision status: Green, nominal. Routine monitoring active.`
    }

    try {
      const utterance = new SpeechSynthesisUtterance(speechText)
      utterance.rate = 0.95

      const voices = window.speechSynthesis.getVoices()
      if (voices && voices.length > 0) {
        const preferredVoice = voices.find(v => v.lang.startsWith('en')) || voices[0]
        if (preferredVoice) utterance.voice = preferredVoice
      }

      utterance.onstart = () => setBroadcastStatus('broadcasting')
      utterance.onend = () => setBroadcastStatus('idle')
      utterance.onerror = () => setBroadcastStatus('unavailable')

      setBroadcastStatus('broadcasting')
      window.speechSynthesis.speak(utterance)
    } catch {
      setBroadcastStatus('unavailable')
    }
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
        description: 'IMMEDIATE: Pre-position emergency response teams. Activate district emergency operations center. Recommend authority assessment and corridor monitoring.',
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
      const [districtResponse, corridorResponse, dashboardResponse] = await Promise.all([
        getJSON<{data: District[]}>('/api/districts'),
        getJSON<{data: Corridor[]}>('/api/corridors'),
        getDashboardSummary().catch(() => null),
      ])
      setDistricts(districtResponse.data)
      setCorridors(corridorResponse.data)
      if (dashboardResponse) setDashboardSummary(dashboardResponse)
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

  const watchlistDistricts = useMemo(() => {
    return filteredDistricts.filter((d) => {
      if (riskFilter !== 'ALL') {
        const level = d.decision?.riskLevel || (d.riskScore == null ? 'DATA_UNAVAILABLE' : d.riskScore >= 75 ? 'RED' : d.riskScore >= 50 ? 'ORANGE' : d.riskScore >= 35 ? 'YELLOW' : 'GREEN')
        if (level !== riskFilter) return false
      }
      if (weatherFilter !== 'ALL') {
        const wStatus = d.rain24h == null ? 'UNAVAILABLE' : 'LIVE'
        if (weatherFilter === 'LIVE' && wStatus !== 'LIVE') return false
        if (weatherFilter === 'UNAVAILABLE' && wStatus !== 'UNAVAILABLE') return false
      }
      if (vulnFilter !== 'ALL') {
        const vStatus = (d as any).vulnerability?.status || 'INSUFFICIENT_DATA'
        if (vulnFilter === 'COMPUTED' && vStatus !== 'COMPUTED') return false
        if (vulnFilter === 'INSUFFICIENT_DATA' && vStatus === 'COMPUTED') return false
      }
      return true
    })
  }, [filteredDistricts, riskFilter, weatherFilter, vulnFilter])

  useEffect(() => {
    if (filteredDistricts.length > 0 && !filteredDistricts.some((d) => d.id === selectedDistrictId)) {
      setSelectedDistrictId(filteredDistricts[0].id)
    }
  }, [filteredDistricts, selectedDistrictId])

  const redCount = filteredDistricts.filter(d => d.riskScore != null && d.riskScore >= 75).length
  const orangeCount = filteredDistricts.filter(d => d.riskScore != null && d.riskScore >= 50 && d.riskScore < 75).length
  const criticalCount = redCount
  const highCount = orangeCount
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
                  <small>{['Regional hazard metrics & overview', 'Terrain analysis & GIS intelligence', 'Risk decomposition & factor analysis', '72-hour risk forecast & projection', 'Crowdsourced incidents & AI verification', 'Priority Alerts & Decision Support', 'Emergency response recommendations', 'Infrastructure monitoring status'][index]}</small>
                </span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="content">
          <section id="overview-step">
            <div style={{ background: 'rgba(220, 38, 38, 0.08)', border: '1px solid rgba(220, 38, 38, 0.3)', color: 'var(--red)', padding: '0.65rem 1rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontWeight: 600 }}>
              <div>
                <strong>⚠️ NON-OFFICIAL DISASTER MANAGEMENT PROTOTYPE</strong> · For authorized internal decision support only. Does not issue official public warnings.
              </div>
              <span style={{ fontSize: '0.72rem', background: 'rgba(220, 38, 38, 0.15)', padding: '0.15rem 0.5rem', borderRadius: '4px', border: '1px solid var(--red)', fontWeight: 700, color: 'var(--red)' }}>P9 SITUATION ROOM</span>
            </div>

            <small className="kicker">01 / OPERATIONAL SITUATION ROOM</small>
            <h1>Landslide Risk Intelligence.<br /><em>Faster Decisions. Safer Communities.</em></h1>
            <p className="lede">GIS-based landslide risk intelligence and decision-support platform for the 8 North Eastern States of India (131 Official Survey of India Districts).</p>
            <button className="primary-button" onClick={() => { setReportOpen(true); setReportResult(null) }}>＋ Log Field Incident</button>

            {/* TOP SITUATION SUMMARY BAR */}
            <div className="panel metrics-panel" style={{ marginTop: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <small className="kicker">SYSTEM SITUATION SUMMARY (P9 SITUATION AWARENESS)</small>
                <small style={{ color: 'var(--text-accent)', fontSize: '0.72rem', fontWeight: 700 }}>Spatial Framework: Official Survey of India (ABDB LGD Integrated)</small>
              </div>

              <div className="metrics">
                <article className="metric neutral">
                  <span className="metric-icon">🗺️</span>
                  <div>
                    <small>Monitored Districts</small>
                    <strong>{dashboardSummary?.monitored_districts_count ?? 131}</strong>
                    <span>8 NE States (SoI Boundaries)</span>
                  </div>
                </article>

                <article className="metric neutral">
                  <span className="metric-icon">📡</span>
                  <div>
                    <small>Weather Feed Health</small>
                    <strong style={{ color: dashboardSummary?.weather_feed_health?.status === 'LIVE' ? '#10b981' : dashboardSummary?.weather_feed_health?.status === 'STALE' ? '#f59e0b' : '#ef4444' }}>
                      {dashboardSummary?.weather_feed_health?.status ?? (apiOnline ? 'LIVE' : 'UNAVAILABLE')}
                    </strong>
                    <span>{dashboardSummary?.weather_feed_health?.live_points ?? 8} Live · {dashboardSummary?.weather_feed_health?.stale_points ?? 0} Stale · {dashboardSummary?.weather_feed_health?.offline_points ?? 0} Offline</span>
                  </div>
                </article>

                <article className={`metric ${criticalCount > 0 ? 'critical' : 'warning'}`}>
                  <span className="metric-icon">⚠️</span>
                  <div>
                    <small>Decision Status Watch</small>
                    <strong>{String(criticalCount + highCount).padStart(2, '0')}</strong>
                    <span>{criticalCount} RED (Emergency ≥75) · {highCount} ORANGE (Warning 50–74)</span>
                  </div>
                </article>

                <article className="metric neutral">
                  <span className="metric-icon">📊</span>
                  <div>
                    <small>Vulnerability Coverage</small>
                    <strong>{dashboardSummary?.vulnerability_coverage_summary?.computed_count ?? 16} / {dashboardSummary?.vulnerability_coverage_summary?.total_districts ?? 131}</strong>
                    <span>{dashboardSummary?.vulnerability_coverage_summary?.insufficient_data_count ?? 115} Insufficient Data</span>
                  </div>
                </article>

                <article className="metric neutral">
                  <span className="metric-icon">🛣️</span>
                  <div>
                    <small>Corridor Watch</small>
                    <strong>{corridors.length} Corridors</strong>
                    <span>{corridors.filter(c => c.status !== 'OPEN').length} Restricted / Blocked</span>
                  </div>
                </article>
              </div>
            </div>

            {/* DISTRICT WATCHLIST TABLE & MULTI-CRITERION FILTERS */}
            <div className="panel" style={{ marginTop: '1.25rem' }}>
              <div className="panel-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <small className="kicker">DISTRICT WATCHLIST &amp; RISK DECISION MATRIX</small>
                  <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)', fontWeight: 700 }}>Filtered Districts ({watchlistDistricts.length} / {filteredDistricts.length})</h3>
                </div>

                {/* FILTERS */}
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem', fontWeight: 600 }}>
                    Risk Level:
                    <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)} style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', background: 'var(--panel-bg)', color: 'var(--text-primary)', border: '1px solid var(--line)', fontSize: '0.72rem', fontWeight: 600 }}>
                      <option value="ALL">All Levels</option>
                      <option value="RED">RED (Critical)</option>
                      <option value="ORANGE">ORANGE (High)</option>
                      <option value="YELLOW">YELLOW (Elevated)</option>
                      <option value="GREEN">GREEN (Low)</option>
                      <option value="DATA_UNAVAILABLE">DATA UNAVAILABLE</option>
                    </select>
                  </label>

                  <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem', fontWeight: 600 }}>
                    Weather:
                    <select value={weatherFilter} onChange={(e) => setWeatherFilter(e.target.value)} style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', background: 'var(--panel-bg)', color: 'var(--text-primary)', border: '1px solid var(--line)', fontSize: '0.72rem', fontWeight: 600 }}>
                      <option value="ALL">All Status</option>
                      <option value="LIVE">LIVE Weather</option>
                      <option value="UNAVAILABLE">Weather Unavailable</option>
                    </select>
                  </label>

                  <label style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem', fontWeight: 600 }}>
                    Vulnerability:
                    <select value={vulnFilter} onChange={(e) => setVulnFilter(e.target.value)} style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', background: 'var(--panel-bg)', color: 'var(--text-primary)', border: '1px solid var(--line)', fontSize: '0.72rem', fontWeight: 600 }}>
                      <option value="ALL">All Coverage</option>
                      <option value="COMPUTED">Acquired Score</option>
                      <option value="INSUFFICIENT_DATA">Insufficient Data</option>
                    </select>
                  </label>
                </div>
              </div>

              {/* TABLE */}
              <div style={{ overflowX: 'auto', marginTop: '0.75rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ background: 'var(--table-header-bg)', color: 'var(--text-primary)', borderBottom: '1px solid var(--line)' }}>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>State</th>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>District</th>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>Modeled Risk Score</th>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>Decision Status</th>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>Confidence</th>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>Weather</th>
                      <th style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 700 }}>P7C Exposure</th>
                      <th style={{ padding: '0.5rem 0.6rem', textAlign: 'right', color: 'var(--text-primary)', fontWeight: 700 }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlistDistricts.map((district) => {
                      const level = district.decision?.riskLevel || (district.riskScore == null ? 'DATA_UNAVAILABLE' : district.riskScore >= 75 ? 'RED' : district.riskScore >= 50 ? 'ORANGE' : district.riskScore >= 35 ? 'YELLOW' : 'GREEN')
                      const riskBand = district.riskScore == null ? 'N/A' : district.riskScore >= 80 ? 'CRITICAL' : district.riskScore >= 60 ? 'HIGH' : district.riskScore >= 40 ? 'MODERATE' : 'LOW'
                      const isSelected = district.id === selectedDistrictId
                      return (
                        <tr
                          key={district.id}
                          style={{
                            borderBottom: '1px solid var(--line)',
                            background: isSelected ? 'var(--badge-blue-bg)' : 'transparent',
                            cursor: 'pointer',
                          }}
                          onClick={() => { setSelectedDistrictId(district.id); navigateTo('xai-step') }}
                        >
                          <td style={{ padding: '0.5rem 0.6rem', color: 'var(--text-secondary)' }}>{district.state}</td>
                          <td style={{ padding: '0.5rem 0.6rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {district.name} {isSelected && <span style={{ color: 'var(--text-accent)', fontSize: '0.7rem', fontWeight: 700 }}>◄ Active</span>}
                          </td>
                          <td style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                            {district.riskScore != null ? (
                              <span>
                                <strong>{district.riskScore} / 100</strong> <span style={{ fontSize: '0.68rem', color: riskBand === 'CRITICAL' ? 'var(--red)' : riskBand === 'HIGH' ? 'var(--amber)' : 'var(--text-muted)', fontWeight: 700 }}>({riskBand})</span>
                              </span>
                            ) : <span style={{ color: 'var(--red)', fontWeight: 700 }}>DATA UNAVAILABLE</span>}
                          </td>
                          <td style={{ padding: '0.5rem 0.6rem' }}>
                            <span style={{
                              padding: '0.15rem 0.4rem',
                              borderRadius: '3px',
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              background: level === 'RED' ? '#d73c50' : level === 'ORANGE' ? '#f8961e' : level === 'YELLOW' ? '#e9c46a' : level === 'GREEN' ? '#2f9b72' : '#6b7280',
                              color: '#fff'
                            }}>
                              {level === 'RED' ? 'RED (Emergency)' : level === 'ORANGE' ? 'ORANGE (Warning)' : level === 'YELLOW' ? 'YELLOW (Elevated)' : level === 'GREEN' ? 'GREEN (Nominal)' : level}
                            </span>
                          </td>
                          <td style={{ padding: '0.5rem 0.6rem', color: 'var(--text-secondary)' }}>{district.decision?.confidence || (district.confidence > 0 ? 'HIGH' : 'UNAVAILABLE')}</td>
                          <td style={{ padding: '0.5rem 0.6rem' }}>
                            <span style={{ color: district.rain24h != null ? 'var(--green)' : 'var(--red)', fontSize: '0.72rem', fontWeight: 700 }}>
                              {district.rain24h != null ? `${district.rain24h}mm` : 'UNAVAILABLE'}
                            </span>
                          </td>
                          <td style={{ padding: '0.5rem 0.6rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                            {(() => {
                              const v = (district as any).vulnerability
                              if (loading && !v) {
                                return <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>LOADING…</span>
                              }

                              if (!v) {
                                return <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>UNAVAILABLE</span>
                              }

                              const vScore = v.composite_vulnerability_score
                              const vStatus = v.status || 'UNAVAILABLE'
                              const avail = v.available_domains_count ?? 0
                              const total = v.total_domains_count ?? 5

                              let statusTag = ''
                              if (vStatus === 'COMPUTED' || vStatus === 'FULL') {
                                statusTag = `FULL · ${avail}/${total} domains`
                              } else if (vStatus === 'PARTIAL') {
                                statusTag = `PARTIAL · ${avail}/${total} domains`
                              } else if (vStatus === 'INSUFFICIENT' || vStatus === 'INSUFFICIENT_DATA') {
                                statusTag = `INSUFFICIENT · ${avail}/${total} domains`
                              } else {
                                statusTag = 'UNAVAILABLE'
                              }

                              if (vScore != null) {
                                return (
                                  <div>
                                    <strong>{vScore} / 100</strong>
                                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600, marginTop: '2px' }}>{statusTag}</div>
                                  </div>
                                )
                              }

                              return <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', fontWeight: 600 }}>{statusTag}</span>
                            })()}
                          </td>
                          <td style={{ padding: '0.5rem 0.6rem', textAlign: 'right' }}>
                            <button
                              type="button"
                              className="secondary-button"
                              style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
                              onClick={(e) => { e.stopPropagation(); setSelectedDistrictId(district.id); navigateTo('xai-step') }}
                            >
                              Inspect →
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
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
                      <small style={{ color: 'var(--text-accent)', fontWeight: 600 }}>Boundary: Official Survey of India (ABDB LGD {(district as any).dist_lgd || 'Integrated'})</small><br />
                      <small style={{ color: 'var(--text-muted)', fontWeight: 600 }}>DEM (NASADEM 30m): Elev {(district as any).terrain?.elevation_m ?? (district as any).terrain?.elevation ?? 'N/A'}m · Slope {(district as any).terrain?.slope_deg ?? (district as any).terrain?.slope ?? 'N/A'}°</small>
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
                <span><strong style={{ color: 'var(--text-primary)', marginRight: '0.4rem', fontWeight: 700 }}>MODELED RISK SCORE:</strong><i className="legend red" /> Critical (≥80)　<i className="legend cyan" /> High (60–79)　<i className="legend violet" /> Moderate (40–59)　<i className="legend green" /> Low (&lt;40)</span>
                <small style={{ display: 'block', marginTop: '0.2rem', color: 'var(--text-muted)', fontWeight: 600 }}>PROTOTYPE DECISION STATUS: RED (Emergency ≥75) · ORANGE (Warning 50–74) · YELLOW (Elevated 35–49) · GREEN (Nominal &lt;35)</small>
                <small style={{ color: 'var(--text-secondary)' }}>8-State Coverage Configured · Official Survey of India (ABDB) Boundaries Integrated (131 Districts) · Risk Feed: {apiOnline ? 'Live API' : 'Offline Fallback'}</small>
              </div>
            </div>
          </section>

          <section id="xai-step" className="section">
            <small className="kicker">03 / EXPLAINABLE AI ENGINE &amp; DECISION SUPPORT</small>
            <h2>Landslide Risk Breakdown: {activeDistrict?.name || 'Selected District'}</h2>
            <div className="panel">
              <div className="panel-head">
                <small className="kicker">FACTOR DECOMPOSITION MATRIX · NEXSOLVE DECISION SUPPORT</small>
                <span className="score">PREDICTED RISK SCORE <b>{riskLoading ? 'LOADING' : (riskPrediction?.riskScore ?? activeDistrict?.riskScore) != null ? `${riskPrediction?.riskScore ?? activeDistrict?.riskScore} / 100` : 'DATA UNAVAILABLE'}</b></span>
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
                    <small>Relative model signal {Math.round(factor.impact)} · {riskPrediction?.modelSource ?? activeDistrict?.modelSource}</small>
                  </article>
                ))}
              </div>
              {(riskPrediction?.decision || activeDistrict?.decision) && (
                <div className="decision-card" style={{ marginTop: '1rem', padding: '1rem', background: 'var(--box-bg-subtle)', borderRadius: '6px', border: '1px solid var(--box-border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-accent)' }}>NEXSOLVE DECISION SUPPORT ENGINE (P8 EXPLAINABILITY)</span>
                    <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '4px', background: (riskPrediction?.decision || activeDistrict?.decision)?.riskLevel === 'RED' ? '#d73c50' : (riskPrediction?.decision || activeDistrict?.decision)?.riskLevel === 'ORANGE' ? '#f8961e' : (riskPrediction?.decision || activeDistrict?.decision)?.riskLevel === 'YELLOW' ? '#e9c46a' : (riskPrediction?.decision || activeDistrict?.decision)?.riskLevel === 'GREEN' ? '#2f9b72' : '#6b7280', color: '#fff', fontWeight: 700 }}>
                      {(riskPrediction?.decision || activeDistrict?.decision)?.riskLevel} ({(riskPrediction?.decision || activeDistrict?.decision)?.riskLabel})
                    </span>
                  </div>

                  <p style={{ margin: '0.4rem 0', fontSize: '0.875rem', lineHeight: '1.45', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {(riskPrediction?.decision || activeDistrict?.decision)?.explanation}
                  </p>

                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                    <span>Confidence: <strong style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{(riskPrediction?.decision || activeDistrict?.decision)?.confidence}</strong></span>
                    <span>Data Status: <strong style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{(riskPrediction?.decision || activeDistrict?.decision)?.dataStatus}</strong></span>
                    <span>Policy: <strong style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{(riskPrediction?.decision || activeDistrict?.decision)?.policyVersion}</strong></span>
                    <span>Reasons: <strong style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{(riskPrediction?.decision || activeDistrict?.decision)?.reasonCodes.join(', ')}</strong></span>
                  </div>

                  {/* P8 DATA QUALITY & WEATHER PROVENANCE */}
                  <div style={{ marginTop: '0.75rem', padding: '0.6rem', background: 'var(--box-bg-subtle)', borderRadius: '4px', border: '1px solid var(--box-border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem', fontSize: '0.75rem' }}>
                      <strong style={{ color: 'var(--text-accent)', fontWeight: 700 }}>📡 DATA QUALITY &amp; WEATHER PROVENANCE</strong>
                      <span style={{ fontSize: '0.68rem', padding: '0.1rem 0.35rem', borderRadius: '3px', background: riskPrediction?.explainability?.weather_status === 'LIVE' ? 'var(--green)' : riskPrediction?.explainability?.weather_status === 'STALE' ? 'var(--amber)' : '#6b7280', color: '#fff', fontWeight: 700 }}>
                        WEATHER: {riskPrediction?.explainability?.weather_status || 'VERIFIED'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      <span>Source: {riskPrediction?.explainability?.weather_source || 'Open-Meteo / IMD Regional Station Feed'}</span> · 
                      <span> Modeled Input: 7 Production Features (Lat, Lon, 1d/3d/7d Rain, Seasonal Sin/Cos)</span>
                    </div>
                  </div>

                  {/* P8 WHY THIS RESULT & MODEL IMPORTANCES */}
                  <div style={{ marginTop: '0.75rem', padding: '0.6rem', background: 'var(--box-bg-subtle)', borderRadius: '4px', border: '1px solid var(--box-border-subtle)' }}>
                    <strong style={{ fontSize: '0.75rem', color: 'var(--text-primary)', display: 'block', marginBottom: '0.3rem', fontWeight: 700 }}>💡 WHY THIS RESULT? (MODEL-LEVEL FEATURE IMPORTANCE)</strong>
                    <p style={{ margin: '0 0 0.4rem 0', fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                      {riskPrediction?.explainability?.explanation_text || "Rainfall-related features and seasonal patterns contributed to the model's estimated risk."}
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', fontSize: '0.7rem' }}>
                      <span style={{ background: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)', border: '1px solid var(--badge-blue-border)', padding: '0.2rem 0.4rem', borderRadius: '3px', fontWeight: 600 }}>24h Rain Importance: 23.3%</span>
                      <span style={{ background: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)', border: '1px solid var(--badge-blue-border)', padding: '0.2rem 0.4rem', borderRadius: '3px', fontWeight: 600 }}>3d Rain Importance: 22.9%</span>
                      <span style={{ background: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)', border: '1px solid var(--badge-blue-border)', padding: '0.2rem 0.4rem', borderRadius: '3px', fontWeight: 600 }}>7d Rain Importance: 22.5%</span>
                      <span style={{ background: 'var(--box-bg-subtle)', color: 'var(--text-muted)', border: '1px solid var(--box-border-subtle)', padding: '0.2rem 0.4rem', borderRadius: '3px', fontWeight: 600 }}>Local Attribution: False (Conservative Decision Support)</span>
                    </div>
                  </div>

                  {/* P8 HUMAN-IN-THE-LOOP ACTION & CHECKLIST */}
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.6rem', borderTop: '1px solid var(--line)', fontSize: '0.8rem' }}>
                    <div style={{ color: 'var(--amber)', marginBottom: '0.4rem', fontWeight: 600 }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Authority Action:</strong> {(riskPrediction?.decision || activeDistrict?.decision)?.recommendedAction}
                    </div>
                    <strong style={{ fontSize: '0.75rem', color: 'var(--text-primary)', display: 'block', marginBottom: '0.3rem', fontWeight: 700 }}>Human Verification Checklist:</strong>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                      <li>Verify current local weather station rainfall accumulation</li>
                      <li>Inspect recent crowd-sourced field reports and ground observations</li>
                      <li>Verify transport corridor (NH-306 / NH-2) and settlement exposure</li>
                      <li>Confirm evaluation with authorized SDMA/NDMA disaster management personnel</li>
                    </ul>
                  </div>

                  <div style={{ marginTop: '0.6rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <em>{riskPrediction?.explainability?.disclaimer || "NexSolve Prototype Decision Support System — Information for decision support only. Not an official government warning."}</em>
                  </div>
                </div>
              )}
              {exposureRecord && (
                <div className="exposure-card" style={{ marginTop: '1rem', padding: '1rem', background: 'var(--box-bg-subtle)', borderRadius: '6px', border: '1px solid var(--box-border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-accent)' }}>EXPOSURE &amp; VULNERABILITY INTELLIGENCE (P7C)</span>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: '4px', background: exposureRecord.status === 'AVAILABLE' ? 'var(--green)' : exposureRecord.status === 'PARTIAL' ? 'var(--amber)' : '#6b7280', color: '#fff', fontWeight: 700 }}>
                        STATUS: {exposureRecord.status}
                      </span>
                      {exposureRecord.vulnerability_intelligence && (
                        <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: '4px', background: 'var(--badge-blue-bg)', color: 'var(--badge-blue-text)', border: '1px solid var(--badge-blue-border)', fontWeight: 700 }}>
                          DOMAIN COVERAGE: {exposureRecord.vulnerability_intelligence.available_domains_count}/{exposureRecord.vulnerability_intelligence.total_domains_count ?? 5} ({exposureRecord.vulnerability_intelligence.data_completeness_pct}%)
                        </span>
                      )}
                    </div>
                  </div>

                  {exposureRecord.vulnerability_intelligence?.composite_vulnerability_score !== undefined && exposureRecord.vulnerability_intelligence?.composite_vulnerability_score !== null && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0.8rem', background: 'var(--badge-blue-bg)', borderRadius: '4px', borderLeft: '4px solid var(--text-accent)', marginBottom: '0.75rem' }}>
                      <div>
                        <strong style={{ color: 'var(--text-accent)', fontSize: '0.85rem', display: 'block', fontWeight: 700 }}>PROTOTYPE COMPOSITE VULNERABILITY SCORE (0-100)</strong>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Domain-weighted indicator score (Decoupled from ML Risk) · Confidence: <strong style={{ color: 'var(--text-primary)' }}>{exposureRecord.vulnerability_intelligence.confidence}</strong></span>
                      </div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-accent)' }}>
                        {exposureRecord.vulnerability_intelligence.composite_vulnerability_score} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ 100</span>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginTop: '0.5rem', fontSize: '0.8rem' }}>
                    <div style={{ background: 'var(--panel-bg)', padding: '0.6rem', borderRadius: '4px', border: '1px solid var(--line)' }}>
                      <strong style={{ color: 'var(--text-accent)', display: 'block', marginBottom: '0.2rem', fontWeight: 700 }}>🏥 HEALTHCARE FACILITIES</strong>
                      {exposureRecord.healthcare ? (
                        <span style={{ color: 'var(--text-secondary)' }}>{exposureRecord.healthcare.total_facilities} Registered Facilities ({exposureRecord.healthcare.district_hospitals} Hospital, {exposureRecord.healthcare.total_bed_capacity} Beds) <small style={{ color: 'var(--text-muted)', fontWeight: 600 }}>[Ref: {exposureRecord.healthcare.reference_year} MoHFW HFR]</small></span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>Data Unavailable</span>}
                    </div>
                    <div style={{ background: 'var(--panel-bg)', padding: '0.6rem', borderRadius: '4px', border: '1px solid var(--line)' }}>
                      <strong style={{ color: 'var(--text-accent)', display: 'block', marginBottom: '0.2rem', fontWeight: 700 }}>🏫 SCHOOL &amp; SHELTER INFRASTRUCTURE</strong>
                      {exposureRecord.education ? (
                        <span style={{ color: 'var(--text-secondary)' }}>{exposureRecord.education.total_schools} Schools ({exposureRecord.education.total_enrolment} Enrolment) <small style={{ color: 'var(--text-muted)', fontWeight: 600 }}>[Ref: {exposureRecord.education.reference_year} UDISE+]</small></span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>Data Unavailable</span>}
                    </div>
                    <div style={{ background: 'var(--panel-bg)', padding: '0.6rem', borderRadius: '4px', border: '1px solid var(--line)' }}>
                      <strong style={{ color: 'var(--text-accent)', display: 'block', marginBottom: '0.2rem', fontWeight: 700 }}>🛣️ ARTERIAL HIGHWAY CORRIDORS</strong>
                      {exposureRecord.transport ? (
                        <span style={{ color: 'var(--text-secondary)' }}>{exposureRecord.transport.arterial_corridor_count} Corridor ({exposureRecord.transport.arterial_highways?.join(', ')}) · {exposureRecord.transport.arterial_highway_length_km}km <small style={{ color: 'var(--text-muted)', fontWeight: 600 }}>[Ref: {exposureRecord.transport.reference_year} MoRTH GIS]</small></span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>Data Unavailable</span>}
                    </div>
                    <div style={{ background: 'var(--panel-bg)', padding: '0.6rem', borderRadius: '4px', border: '1px solid var(--line)' }}>
                      <strong style={{ color: 'var(--text-accent)', display: 'block', marginBottom: '0.2rem', fontWeight: 700 }}>📊 SOCIO-ECONOMIC VULNERABILITY</strong>
                      {exposureRecord.vulnerability ? (
                        <span style={{ color: 'var(--text-secondary)' }}>MPI Headcount: {exposureRecord.vulnerability.headcount_ratio_pct}% · Housing Deprivation: {exposureRecord.vulnerability.housing_deprived_pct}% · BMTPC Landslide Zone: {exposureRecord.vulnerability.landslide_hazard_zone} <small style={{ color: 'var(--text-muted)', fontWeight: 600 }}>[Ref: 2023 NITI Aayog / BMTPC]</small></span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>Data Unavailable</span>}
                    </div>
                  </div>

                  {exposureRecord.vulnerability_intelligence?.contributing_factors && exposureRecord.vulnerability_intelligence.contributing_factors.length > 0 && (
                    <div style={{ marginTop: '0.75rem', padding: '0.6rem', background: 'var(--panel-bg)', borderRadius: '4px', border: '1px solid var(--line)' }}>
                      <strong style={{ fontSize: '0.75rem', color: 'var(--text-primary)', display: 'block', marginBottom: '0.4rem', fontWeight: 700 }}>CONTRIBUTING VULNERABILITY FACTORS</strong>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {exposureRecord.vulnerability_intelligence.contributing_factors.map(cf => (
                          <div key={cf.domain_key} style={{ fontSize: '0.72rem', background: 'var(--box-bg-subtle)', padding: '0.25rem 0.5rem', borderRadius: '3px', border: '1px solid var(--line)' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>{cf.domain_name}:</span> <strong style={{ color: 'var(--text-accent)', fontWeight: 700 }}>Normalized contribution: {cf.contribution_pct}%</strong> <span style={{ color: 'var(--text-muted)' }}>(norm: {cf.normalized_score})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: '0.5rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <em>{exposureRecord.vulnerability_intelligence?.disclaimer || "NexSolve Prototype Exposure/Vulnerability Support — Information for decision support only."}</em>
                  </div>
                </div>
              )}
              <div className="simulator">
                <b>⚡ Risk engine status:</b>
                <span>{riskPrediction ? `POST /api/risk · ${riskPrediction.status} · confidence ${riskPrediction.confidence}%` : apiOnline ? `District feed connected · confidence ${activeDistrict?.confidence ?? 0}%` : 'Offline fallback active'}</span>
                {riskError && <span className="risk-error">{riskError}</span>}
                <small className="terrain-context-note">
                  Terrain context available from processed ~30m DEM; not used by the trained Random Forest prediction model.
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
            <small className="kicker">06 / PRIORITY ALERTS &amp; DECISION SUPPORT QUEUE</small>
            <h2>Priority Alerts &amp; Decision Support</h2>
            <div className="panel list-panel" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <small className="kicker">CURRENT PRIORITY QUEUE</small>
                <small style={{ color: 'var(--text-kicker)', fontSize: '0.72rem', fontWeight: 600 }}>P6 Decision Thresholds: RED (≥75) · ORANGE (50–74)</small>
              </div>

              {districts.filter(d => {
                const level = d.decision?.riskLevel || (d.riskScore == null ? 'DATA_UNAVAILABLE' : d.riskScore >= 75 ? 'RED' : d.riskScore >= 50 ? 'ORANGE' : 'GREEN')
                return level === 'RED' || level === 'ORANGE'
              }).length > 0 ? (
                districts.filter(d => {
                  const level = d.decision?.riskLevel || (d.riskScore == null ? 'DATA_UNAVAILABLE' : d.riskScore >= 75 ? 'RED' : d.riskScore >= 50 ? 'ORANGE' : 'GREEN')
                  return level === 'RED' || level === 'ORANGE'
                }).map((district) => {
                  const level = district.decision?.riskLevel || (district.riskScore! >= 75 ? 'RED' : 'ORANGE')
                  return (
                    <article className="list-row" key={district.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.8rem 1rem', background: 'var(--box-bg-subtle)', borderRadius: '4px', border: '1px solid var(--line)', marginBottom: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                        <span className={`severity ${level === 'RED' ? 'critical' : 'warning'}`} style={{ padding: '0.2rem 0.5rem', borderRadius: '3px', fontWeight: 700, fontSize: '0.7rem' }}>
                          {level === 'RED' ? 'RED (Emergency)' : 'ORANGE (Warning)'}
                        </span>
                        <div>
                          <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary)', display: 'block', fontWeight: 700 }}>{district.name}, {district.state}</strong>
                          <small style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            Modeled Risk Score: <strong style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{district.riskScore} / 100</strong> · Weather: {district.rain24h != null ? `${district.rain24h}mm 24h rain` : 'Feed Connected'} · Confidence: {district.decision?.confidence || 'HIGH'}
                          </small>
                          <span style={{ display: 'block', marginTop: '0.2rem', fontSize: '0.73rem', color: 'var(--text-secondary)' }}>
                            <strong>Action:</strong> {district.decision?.recommendedAction || 'Escalate to authorized disaster-management personnel for verification.'}
                          </span>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="secondary-button"
                        style={{ minHeight: '36px', padding: '0 12px', fontSize: '0.72rem' }}
                        onClick={() => { setSelectedDistrictId(district.id); navigateTo('xai-step') }}
                      >
                        Inspect Queue Item →
                      </button>
                    </article>
                  )
                })
              ) : (
                <div style={{ padding: '1.75rem 1.25rem', textAlign: 'center', background: 'var(--box-bg-subtle)', borderRadius: '6px', border: '1px solid var(--line)' }}>
                  <div style={{ fontSize: '1.8rem', marginBottom: '0.4rem' }}>✅</div>
                  <h4 style={{ margin: '0 0 0.3rem 0', fontSize: '1.05rem', color: 'var(--text-primary)', fontWeight: 700 }}>NO ACTIVE PRIORITY ALERTS</h4>
                  <p style={{ margin: '0 0 0.6rem 0', fontSize: '0.88rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    No districts currently meet the prototype RED/ORANGE decision thresholds.
                  </p>
                  
                  <div style={{ margin: '0.8rem auto 0.9rem auto', maxWidth: '520px', padding: '0.75rem 1rem', background: 'var(--panel-subtle)', borderRadius: '6px', border: '1px solid var(--line)', textAlign: 'left' }}>
                    <small className="kicker" style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-kicker)', fontWeight: 700 }}>PROTOTYPE DECISION THRESHOLDS REFERENCE</small>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.65' }}>
                      <li><strong style={{ color: 'var(--red)' }}>RED ≥75</strong> — Emergency review</li>
                      <li><strong style={{ color: 'var(--amber)' }}>ORANGE 50–74</strong> — Warning review</li>
                      <li><strong style={{ color: 'var(--amber)' }}>YELLOW 35–49</strong> — Enhanced monitoring</li>
                      <li><strong style={{ color: 'var(--green)' }}>GREEN &lt;35</strong> — Baseline monitoring</li>
                    </ul>
                  </div>

                  <p style={{ margin: '0.5rem 0 0.8rem 0', fontSize: '0.82rem', color: 'var(--text-kicker)', fontWeight: 600 }}>
                    131 official Survey of India districts monitored
                  </p>

                  <div style={{ paddingTop: '0.6rem', borderTop: '1px solid var(--line)', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                    <em>PROTOTYPE / INTERNAL DECISION SUPPORT ONLY — NexSolve does not issue official government warnings or evacuation orders.</em>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section id="response-step" className="section">
            <small className="kicker">07 / RESPONSE MATRIX · NEXSOLVE DECISION SUPPORT</small>
            <h2>{activeDistrict?.name || 'Selected District'} {getResponseRecommendation(activeDistrict?.riskScore ?? undefined, activeDistrict?.status).title}</h2>
            <div className="panel response" style={{ padding: '1.25rem' }}>
              <span style={{ fontSize: '1.8rem' }}>🚨</span>
              <div>
                <h3 style={{ color: 'var(--text-primary)' }}>{getResponseRecommendation(activeDistrict?.riskScore ?? undefined, activeDistrict?.status).heading}</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.45', margin: '0.4rem 0' }}>
                  Response recommendation is driven by the current {activeDistrict?.name || 'selected district'} decision state: <b>{(activeDistrict?.decision || riskPrediction?.decision)?.riskLevel || activeDistrict?.status}</b> (Modeled Risk Score: {activeDistrict?.riskScore ?? 'DATA UNAVAILABLE'} / 100). {(activeDistrict?.decision || riskPrediction?.decision)?.recommendedAction || getResponseRecommendation(activeDistrict?.riskScore ?? undefined, activeDistrict?.status).description}
                </p>
                <div style={{ margin: '0.6rem 0 0.8rem 0', fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                  <em>Browser audio preview for authorized personnel review. Not an official public warning. Does NOT replace official government emergency alerts or trigger automated public evacuations.</em>
                </div>
                <button
                  className="primary-button"
                  onClick={broadcastWarning}
                  disabled={broadcastStatus === 'unavailable'}
                  aria-live="polite"
                  style={{ minHeight: '44px', padding: '0 18px', fontSize: '0.8rem', fontWeight: 700 }}
                >
                  📢 {broadcastStatus === 'broadcasting' ? '🔊 Speaking Audio Advisory... (Click to Stop)' : 'Play Decision-Support Audio'}
                </button>
                {broadcastStatus === 'unavailable' && <small className="broadcast-status error" style={{ display: 'block', marginTop: '0.5rem', color: 'var(--red)', fontWeight: 600 }}>Browser audio is unavailable. Please enable browser speech synthesis or use another supported browser.</small>}
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
            <div style={{ background: 'rgba(220, 38, 38, 0.08)', border: '1px solid rgba(220, 38, 38, 0.3)', color: 'var(--red)', padding: '0.75rem 1rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.8rem', textAlign: 'center', fontWeight: 600 }}>
              <strong>⚠️ PROTOTYPE / NON-OFFICIAL DISASTER MANAGEMENT SYSTEM</strong><br />
              NexSolve is an internal decision-support prototype. It does NOT possess official warning authority and MUST NOT issue public evacuation orders or official emergency broadcasts without human authorization from SDMA/NDMA.
            </div>
            <b>NEXSOLVE</b> — Enterprise Landslide &amp; Hazard Intelligence Platform (NexSolve Decision Support System).<br />
            Risk feed powered by promoted Candidate A Random Forest model (`candidate_a_rf_v1` v1.1.0) and central risk decision engine (`risk_policy.json` v1.0.0-PROTOTYPE).
          </footer>
        </main>
      </div>
    </div>
  )
}

export default App
