import type { ForecastPoint, District } from '../lib/api'

type ForecastSectionProps = {
  activeDistrict?: District
  forecast: ForecastPoint[]
  forecastSource: string
  forecastLive: boolean
  forecastLoading: boolean
  forecastError: string | null
}

export default function ForecastSection({
  activeDistrict,
  forecast,
  forecastSource,
  forecastLive,
  forecastLoading,
  forecastError,
}: ForecastSectionProps) {
  const peakPoint = forecast.length ? [...forecast].sort((a, b) => b.riskScore - a.riskScore)[0] : null
  const w1 = forecast.slice(0, 8)
  const w2 = forecast.slice(8, 16)
  const w3 = forecast.slice(16, 24)

  const calcWindowSummary = (pts: ForecastPoint[]) => {
    if (!pts.length) return { maxRisk: 0, sumRain: 0, level: 'GREEN' }
    const maxRisk = Math.max(...pts.map((p) => p.riskScore))
    const sumRain = pts.reduce((acc, p) => acc + p.rainfall, 0)
    const level = maxRisk >= 75 ? 'RED' : maxRisk >= 50 ? 'ORANGE' : maxRisk >= 35 ? 'YELLOW' : 'GREEN'
    return { maxRisk, sumRain, level }
  }

  const sum1 = calcWindowSummary(w1)
  const sum2 = calcWindowSummary(w2)
  const sum3 = calcWindowSummary(w3)

  return (
    <section id="forecast-step" className="step-card forecast-layout-card">
      <div className="section-header">
        <div>
          <h2>72-Hour Predictive Risk Forecast</h2>
          <p className="subtext">
            Forward risk projection for <strong>{activeDistrict?.name || 'Selected Location'}</strong> based on IMD GFS weather ensemble forecasts.
          </p>
        </div>
        <div className="forecast-source-badge">
          <span className={`status-dot ${forecastLive ? 'live' : 'historical'}`} />
          {forecastSource || 'IMD GFS Ensemble'}
        </div>
      </div>

      {forecastError && <div className="inline-error-banner">{forecastError}</div>}

      {forecastLoading ? (
        <div className="card-skeleton">Loading 72-hour forecast projection...</div>
      ) : forecast.length === 0 ? (
        <div className="empty-forecast-notice">Forecast projections currently unavailable for this location.</div>
      ) : (
        <>
          <div className="forecast-grid-summary">
            {peakPoint && (
              <div className="forecast-card peak-card">
                <div className="forecast-card-label">PEAK RISK HORIZON</div>
                <div className="forecast-card-value">{peakPoint.riskScore} / 100</div>
                <div className="forecast-card-sub">
                  Expected Peak: <strong>{new Date(peakPoint.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</strong>
                </div>
              </div>
            )}

            <div className="forecast-card window-card">
              <div className="forecast-card-label">NEXT 24 HOURS</div>
              <div className={`forecast-card-value level-${sum1.level.toLowerCase()}`}>{sum1.maxRisk} / 100</div>
              <div className="forecast-card-sub">Cum. Rainfall: <strong>{sum1.sumRain.toFixed(1)} mm</strong></div>
            </div>

            <div className="forecast-card window-card">
              <div className="forecast-card-label">24 – 48 HOURS</div>
              <div className={`forecast-card-value level-${sum2.level.toLowerCase()}`}>{sum2.maxRisk} / 100</div>
              <div className="forecast-card-sub">Cum. Rainfall: <strong>{sum2.sumRain.toFixed(1)} mm</strong></div>
            </div>

            <div className="forecast-card window-card">
              <div className="forecast-card-label">48 – 72 HOURS</div>
              <div className={`forecast-card-value level-${sum3.level.toLowerCase()}`}>{sum3.maxRisk} / 100</div>
              <div className="forecast-card-sub">Cum. Rainfall: <strong>{sum3.sumRain.toFixed(1)} mm</strong></div>
            </div>
          </div>

          <div className="forecast-chart-container">
            <h4>72-Hour Risk Trajectory Chart</h4>
            <div className="chart-bars-flex">
              {forecast.map((pt, idx) => {
                const heightPct = Math.max(8, pt.riskScore)
                const barColor = pt.riskScore >= 75 ? '#ef4444' : pt.riskScore >= 50 ? '#f97316' : pt.riskScore >= 35 ? '#eab308' : '#22c55e'
                return (
                  <div key={idx} className="chart-bar-column" title={`${pt.timestamp}: Risk ${pt.riskScore}, Rain ${pt.rainfall}mm`}>
                    <div className="bar-fill" style={{ height: `${heightPct}%`, backgroundColor: barColor }} />
                    <span className="bar-label">{idx % 4 === 0 ? new Date(pt.timestamp).getHours() + 'h' : ''}</span>
                  </div>
                )
              })}
            </div>
          </div>

          <details className="calculation-details">
            <summary>How is this calculated?</summary>
            <div className="details-body">
              <p>
                The 72-hour landslide risk forecast integrates quantitative 3-hour precipitation forecasts from the India Meteorological Department (IMD) Global Forecasting System (GFS) with local slope angles and antecedent soil saturation memory.
              </p>
              <p>
                Risk scores are evaluated against P6 production decision thresholds: <strong>GREEN (&lt;35)</strong> nominal, <strong>YELLOW (&ge;35)</strong> elevated, <strong>ORANGE (&ge;50)</strong> high alert, and <strong>RED (&ge;75)</strong> critical emergency response.
              </p>
            </div>
          </details>
        </>
      )}
    </section>
  )
}
