import type { RainfallData, DashboardSummary } from '../lib/api'

type SystemStatusSectionProps = {
  connectionState: 'CONNECTING' | 'LIVE' | 'DEGRADED' | 'UNAVAILABLE'
  activeModelMeta: { id: string; version: string; sha256: string } | null
  modelReadinessState: 'LOADING' | 'READY' | 'UNAVAILABLE'
  rainfallData: RainfallData | null
  dashboardSummary: DashboardSummary | null
  lastUpdated: string
  broadcastStatus: 'idle' | 'broadcasting' | 'complete' | 'unavailable'
  broadcastWarning: () => void
  handleWarmupAndRefresh: (isManual?: boolean) => Promise<void>
}

export default function SystemStatusSection({
  connectionState,
  activeModelMeta,
  modelReadinessState,
  rainfallData,
  dashboardSummary,
  lastUpdated,
  broadcastStatus,
  broadcastWarning,
  handleWarmupAndRefresh,
}: SystemStatusSectionProps) {
  return (
    <section id="response-step" className="step-card status-layout-card">
      <div className="section-header">
        <div>
          <h2>System Status & Decision Advisory</h2>
          <p className="subtext">
            Real-time system health telemetry, service readiness probes, model provenance, and decision-support disclaimers.
          </p>
        </div>
        <button
          className="refresh-button"
          onClick={() => void handleWarmupAndRefresh(true)}
        >
          {lastUpdated ? `Last probe ${lastUpdated}` : 'Run Health Probe'}
        </button>
      </div>

      <div className="status-telemetry-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="op-card">
          <div className="op-card-header">
            <span className="op-card-title">BACKEND & API CONNECTIVITY</span>
            <span className={`op-card-badge ${connectionState === 'LIVE' ? 'green' : connectionState === 'CONNECTING' ? 'blue' : 'amber'}`}>
              {connectionState === 'LIVE' ? 'SYSTEM READY' : connectionState === 'CONNECTING' ? 'CONNECTING…' : 'DEGRADED'}
            </span>
          </div>
          <div className="op-card-body">
            <p className="op-stat-desc">
              FastAPI Uvicorn service endpoints probed (`/api/ready`, `/api/districts`, `/api/corridors`).
            </p>
            <div className="subtext" style={{ marginTop: '0.5rem' }}>
              Probe Status: <strong>{connectionState === 'LIVE' ? 'Operational' : 'Rechecking service health…'}</strong>
            </div>
          </div>
        </div>

        <div className="op-card">
          <div className="op-card-header">
            <span className="op-card-title">ACTIVE ML MODEL PROVENANCE</span>
            <span className={`op-card-badge ${modelReadinessState === 'READY' ? 'green' : modelReadinessState === 'LOADING' ? 'blue' : 'amber'}`}>
              {modelReadinessState === 'READY' ? 'LOADED & VERIFIED' : modelReadinessState === 'LOADING' ? 'LOADING…' : 'UNAVAILABLE'}
            </span>
          </div>
          <div className="op-card-body">
            <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
              <div>Active Model: <strong>{activeModelMeta?.id || (modelReadinessState === 'LOADING' ? 'Loading…' : 'Unavailable')}</strong></div>
              <div>Model Version: <strong>{activeModelMeta?.version ? `v${activeModelMeta.version}` : modelReadinessState === 'LOADING' ? 'Loading…' : 'Unavailable'}</strong></div>
              <div>Feature Contract: <strong>7-Feature Production Contract</strong></div>
              <div style={{ marginTop: '0.3rem', fontSize: '0.8rem', wordBreak: 'break-all' }}>
                SHA-256: <code>{activeModelMeta?.sha256 || (modelReadinessState === 'LOADING' ? 'Loading…' : 'Unavailable')}</code>
              </div>
            </div>
          </div>
        </div>

        <div className="op-card">
          <div className="op-card-header">
            <span className="op-card-title">WEATHER FEED PROVENANCE</span>
            <span className={`op-card-badge ${rainfallData?.is_live ? 'green' : 'amber'}`}>
              {rainfallData?.is_live ? 'LIVE FEED ACTIVE' : 'STALE / DEGRADED'}
            </span>
          </div>
          <div className="op-card-body">
            <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
              <div>Provider: <strong>{rainfallData?.source || 'Open-Meteo current/hourly precipitation'}</strong></div>
              <div>24h Peak Value: <strong>{rainfallData?.rainfall_24h != null ? `${rainfallData.rainfall_24h} mm` : 'N/A'}</strong></div>
              <p className="op-stat-desc" style={{ marginTop: '0.4rem' }}>
                Strict policy: No historical values are substituted when live weather feeds disconnect.
              </p>
            </div>
          </div>
        </div>

        <div className="op-card">
          <div className="op-card-header">
            <span className="op-card-title">GIS & BOUNDARY FRAMEWORK</span>
            <span className="op-card-badge green">AUTHORITATIVE</span>
          </div>
          <div className="op-card-body">
            <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
              <div>Administrative Geometry: <strong>Survey of India ABDB GeoJSON</strong></div>
              <div>Monitored Framework: <strong>{dashboardSummary?.monitored_districts_count ?? 131} Official Districts</strong></div>
              <div>Operational Risk Nodes: <strong>{dashboardSummary?.operational_nodes_count ?? 9} Locations</strong></div>
              <div>Terrain Data: <strong>NASADEM ~30m DEM Terrain Slope</strong></div>
            </div>
          </div>
        </div>
      </div>

      <div className="op-card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--accent-blue, #3b82f6)' }}>
        <div className="op-card-header">
          <span className="op-card-title">P6 DECISION ENGINE POLICY & AUDIBILITY</span>
          <span className="op-card-badge blue">DECISION SUPPORT</span>
        </div>
        <div className="op-card-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <p className="op-stat-desc" style={{ marginBottom: '0.5rem' }}>
                Decision thresholds: <strong>0.35 (Elevated) / 0.50 (Warning) / 0.75 (Emergency)</strong>. Modeled risk probability is decoupled from vulnerability scores.
              </p>
              <div className="subtext">
                Broadcast status: <strong>{broadcastStatus === 'broadcasting' ? 'Audio Advisory Playing' : broadcastStatus === 'unavailable' ? 'Text-to-speech SpeechSynthesis unavailable in browser' : 'Idle'}</strong>
              </div>
            </div>
            <button className="action-button primary" onClick={broadcastWarning}>
              {broadcastStatus === 'broadcasting' ? '🔊 Stop Advisory' : '🔊 Listen to Audio Advisory'}
            </button>
          </div>
        </div>
      </div>

      <div className="provenance-disclaimer-note" style={{ padding: '1rem', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
        <h4 style={{ color: 'var(--red, #ef4444)', marginTop: 0, marginBottom: '0.4rem' }}>⚠️ Decision Support Operational Disclaimer</h4>
        <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.5' }}>
          <strong>NexSolve is an automated risk-intelligence decision-support framework.</strong> It does <strong>NOT</strong> autonomously issue official government warnings, public alerts, or evacuation orders. All model outputs, weather observations, and risk estimates require ground verification by authorized disaster management personnel (SDMA/NDRF) prior to operational decision deployment.
        </p>
      </div>
    </section>
  )
}
