import { useState } from 'react'
import { motion } from 'motion/react'
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
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const peakPoint = forecast.length ? [...forecast].sort((a, b) => b.riskScore - a.riskScore)[0] : null
  const peakIndex = peakPoint ? forecast.findIndex((p) => p.timestamp === peakPoint.timestamp) : -1

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

  const activePoint = hoveredIdx !== null && forecast[hoveredIdx] ? forecast[hoveredIdx] : peakPoint

  const getRiskLevel = (score: number) => {
    if (score >= 75) return { label: 'CRITICAL', colorClass: 'red' }
    if (score >= 50) return { label: 'HIGH ALERT', colorClass: 'orange' }
    if (score >= 35) return { label: 'ELEVATED', colorClass: 'yellow' }
    return { label: 'NOMINAL', colorClass: 'green' }
  }

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
          {forecastLive ? (forecastSource || 'IMD GFS Ensemble') : 'Forecast source: unavailable'}
        </div>
      </div>

      {forecastError && <div className="inline-error-banner">{forecastError}</div>}

      {forecastLoading ? (
        <div className="card-skeleton">Loading 72-hour forecast projection...</div>
      ) : forecast.length === 0 ? (
        <div className="forecast-unavailable-panel">
          <div className="unavailable-header">
            <span className="warning-icon">⚠️</span>
            <h4>FORECAST DATA UNAVAILABLE</h4>
          </div>
          <p className="unavailable-text">
            Live forecast data could not be retrieved for <strong>{activeDistrict?.name || 'this location'}</strong>. No historical values are substituted.
          </p>
          <div className="unavailable-status-grid">
            <div className="status-item">
              <span className="item-label">Forecast Status</span>
              <span className="item-value offline">UNAVAILABLE</span>
            </div>
            <div className="status-item">
              <span className="item-label">Risk Projection</span>
              <span className="item-value neutral">NOT EVALUABLE</span>
            </div>
          </div>
        </div>
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
            <div className="chart-top-bar">
              <div className="chart-heading">
                <h4>72-Hour Risk Trajectory</h4>
                <span className="chart-sub">Monospace Risk Intelligence Timeline</span>
              </div>
              <div className="chart-legend-row">
                <span className="legend-chip green"><span className="legend-dot green" /> &lt;35 Nominal</span>
                <span className="legend-chip yellow"><span className="legend-dot yellow" /> 35–49 Elevated</span>
                <span className="legend-chip orange"><span className="legend-dot orange" /> 50–74 High</span>
                <span className="legend-chip red"><span className="legend-dot red" /> ≥75 Critical</span>
              </div>
            </div>

            {activePoint && (
              <div className="chart-tooltip-bar">
                <div className="tooltip-item">
                  <span className="tooltip-label">TIMESTAMP</span>
                  <span className="tooltip-val">
                    {new Date(activePoint.timestamp).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div className="tooltip-item">
                  <span className="tooltip-label">MODELED RISK</span>
                  <span className={`tooltip-val risk-text-${getRiskLevel(activePoint.riskScore).colorClass}`}>
                    {activePoint.riskScore} / 100
                  </span>
                </div>
                <div className="tooltip-item">
                  <span className="tooltip-label">PRECIPITATION</span>
                  <span className="tooltip-val">{activePoint.rainfall.toFixed(1)} mm</span>
                </div>
                <div className="tooltip-item">
                  <span className="tooltip-label">STATUS</span>
                  <span className={`tooltip-badge badge-${getRiskLevel(activePoint.riskScore).colorClass}`}>
                    {hoveredIdx === peakIndex ? '★ PEAK RISK' : getRiskLevel(activePoint.riskScore).label}
                  </span>
                </div>
              </div>
            )}

            <div className="chart-canvas-wrapper">
              <div className="y-axis-labels">
                <span>100</span>
                <span>75</span>
                <span>50</span>
                <span>35</span>
                <span>0</span>
              </div>

              <div className="chart-plot-container">
                <div className="threshold-line line-75" title="Critical Threshold (75)" />
                <div className="threshold-line line-50" title="High Alert Threshold (50)" />
                <div className="threshold-line line-35" title="Elevated Threshold (35)" />

                <div className="chart-bars-flex">
                  {forecast.map((pt, idx) => {
                    const heightPct = Math.max(6, Math.min(100, pt.riskScore))
                    const isPeak = idx === peakIndex
                    const isHovered = idx === hoveredIdx
                    const level = getRiskLevel(pt.riskScore)

                    return (
                      <div
                        key={idx}
                        className={`chart-bar-column ${isPeak ? 'is-peak' : ''} ${isHovered ? 'is-hovered' : ''}`}
                        onMouseEnter={() => setHoveredIdx(idx)}
                        onMouseLeave={() => setHoveredIdx(null)}
                        onFocus={() => setHoveredIdx(idx)}
                        onBlur={() => setHoveredIdx(null)}
                        tabIndex={0}
                        role="button"
                        aria-label={`Hour ${(idx + 1) * 3}: Risk ${pt.riskScore}, Rain ${pt.rainfall}mm`}
                      >
                        {isPeak && <span className="peak-indicator-dot" title="Peak Risk Horizon" />}
                        <motion.div
                          className={`bar-fill bar-${level.colorClass}`}
                          initial={{ height: 0 }}
                          animate={{ height: `${heightPct}%` }}
                          transition={{ duration: 0.4, delay: idx * 0.015, ease: 'easeOut' }}
                        />
                        <span className="bar-label">
                          {idx % 2 === 0 ? `${idx * 3}h` : ''}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="threshold-gutter">
                <div className="gutter-label label-75">Critical 75</div>
                <div className="gutter-label label-50">High Alert 50</div>
                <div className="gutter-label label-35">Elevated 35</div>
              </div>
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
