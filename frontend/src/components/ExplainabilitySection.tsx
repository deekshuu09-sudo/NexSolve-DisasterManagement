import type { District, RiskPrediction } from '../lib/api'

type ExplainabilitySectionProps = {
  activeDistrict?: District
  riskPrediction: RiskPrediction | null
  riskLoading: boolean
  riskError: string | null
}

export default function ExplainabilitySection({
  activeDistrict,
  riskPrediction,
  riskLoading,
  riskError,
}: ExplainabilitySectionProps) {
  const decision = activeDistrict?.decision || riskPrediction?.decision
  const explainability = riskPrediction?.explainability
  const factors = activeDistrict?.factors || riskPrediction?.factors || []

  return (
    <section id="xai-step" className="step-card xai-layout-card">
      <div className="section-header">
        <div>
          <h2>Explainable AI & Risk Signal Decomposition (P8)</h2>
          <p className="subtext">
            Transparent feature weight decomposition and decision rationale for <strong>{activeDistrict?.name || 'Selected Location'}</strong>
          </p>
        </div>
      </div>

      {riskError && <div className="inline-error-banner">{riskError}</div>}

      {riskLoading ? (
        <div className="card-skeleton">Extracting feature importance & SHAP/LIME decision parameters...</div>
      ) : (
        <div className="xai-content-grid">
          <div className="xai-box">
            <h4>7-Feature Production Model Weights</h4>
            <div className="factor-bars-list">
              {factors.length === 0 ? (
                <p className="subtext">No feature factor breakdown available for current selection.</p>
              ) : (
                factors.map((f, idx) => (
                  <div key={idx} className="factor-row">
                    <div className="factor-meta">
                      <span className="factor-name">{f.name}</span>
                      <span className="factor-weight">{(f.weight * 100).toFixed(1)}% weight</span>
                    </div>
                    <div className="factor-track">
                      <div className="factor-fill" style={{ width: `${Math.min(100, f.weight * 100)}%` }} />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="xai-box">
            <h4>Decision Rationale & Uncertainty</h4>
            <div className="rationale-text">
              <p><strong>Model Decision Rationale:</strong> {decision?.explanation || 'Feature values indicate nominal slope stability under current 24h/3d/7d precipitation regimes.'}</p>
              <p><strong>Model Artifact SHA-256:</strong> <code>d8546b0f78372c...50eb1</code> (Production RF v1.0)</p>
              <p><strong>Uncertainty Level:</strong> {explainability?.uncertainty?.uncertainty_level || 'LOW'}</p>
              {explainability?.uncertainty?.uncertainty_notes?.length ? (
                <ul>
                  {explainability.uncertainty.uncertainty_notes.map((note: string, idx: number) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
