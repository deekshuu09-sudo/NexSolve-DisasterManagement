import type { ImageAnalysis } from '../lib/api'

type FieldIntelligenceSectionProps = {
  reportOpen: boolean
  setReportOpen: (open: boolean) => void
  reportLocation: string
  setReportLocation: (loc: string) => void
  reportLatitude: string
  setReportLatitude: (lat: string) => void
  reportLongitude: string
  setReportLongitude: (lng: string) => void
  reportDescription: string
  setReportDescription: (desc: string) => void
  reportSubmitting: boolean
  reportResult: any
  submittedReports: any[]
  reportImage: File | null
  reportImagePreview: string | null
  imageAnalysis: ImageAnalysis | null
  imageLoading: boolean
  imageError: string | null
  handleImageChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  submitReport: () => Promise<void>
}

export default function FieldIntelligenceSection({
  reportOpen,
  setReportOpen,
  reportLocation,
  setReportLocation,
  reportLatitude,
  setReportLatitude,
  reportLongitude,
  setReportLongitude,
  reportDescription,
  setReportDescription,
  reportSubmitting,
  reportResult,
  submittedReports,
  reportImage,
  reportImagePreview,
  imageAnalysis,
  imageLoading,
  imageError,
  handleImageChange,
  submitReport,
}: FieldIntelligenceSectionProps) {
  return (
    <section id="field-step" className="step-card field-layout-card">
      <div className="section-header">
        <div>
          <h2>Field Incident Observations</h2>
          <p className="subtext">
            Submit and inspect field observation reports and image screening results
          </p>
        </div>
        <button className="btn-primary" onClick={() => setReportOpen(!reportOpen)}>
          {reportOpen ? 'Close Form' : '+ Submit Incident'}
        </button>
      </div>

      {reportOpen && (
        <div style={{ background: 'var(--panel-subtle)', padding: '20px', borderRadius: '8px', border: '1px solid var(--panel-border)', marginBottom: '20px' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '16px' }}>Submit Field Report</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px', marginBottom: '12px' }}>
            <div>
              <label htmlFor="field-report-location" style={{ fontSize: '0.78rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Location / Corridor *</label>
              <input
                id="field-report-location"
                type="text"
                value={reportLocation}
                onChange={(e) => setReportLocation(e.target.value)}
                placeholder="e.g. Champhai Axis"
                style={{ width: '100%', height: '36px', padding: '0 10px', borderRadius: '6px', border: '1px solid var(--panel-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ flex: 1 }}>
                <label htmlFor="field-report-latitude" style={{ fontSize: '0.78rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Lat</label>
                <input
                  id="field-report-latitude"
                  type="text"
                  value={reportLatitude}
                  onChange={(e) => setReportLatitude(e.target.value)}
                  placeholder="23.4756"
                  style={{ width: '100%', height: '36px', padding: '0 10px', borderRadius: '6px', border: '1px solid var(--panel-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)' }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label htmlFor="field-report-longitude" style={{ fontSize: '0.78rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Lng</label>
                <input
                  id="field-report-longitude"
                  type="text"
                  value={reportLongitude}
                  onChange={(e) => setReportLongitude(e.target.value)}
                  placeholder="93.3289"
                  style={{ width: '100%', height: '36px', padding: '0 10px', borderRadius: '6px', border: '1px solid var(--panel-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)' }}
                />
              </div>
            </div>
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label htmlFor="field-report-description" style={{ fontSize: '0.78rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Field Observations *</label>
            <textarea
              id="field-report-description"
              rows={3}
              value={reportDescription}
              onChange={(e) => setReportDescription(e.target.value)}
              placeholder="Describe slope movement, road blockages, or structural impacts..."
              style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid var(--panel-border)', background: 'var(--panel-bg)', color: 'var(--text-primary)' }}
            />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="field-report-image" style={{ fontSize: '0.78rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Incident Photograph (Quality Screening)</label>
            <input id="field-report-image" type="file" accept="image/*" onChange={handleImageChange} style={{ fontSize: '0.85rem' }} />
            {imageLoading && <p className="subtext" style={{ marginTop: '4px' }}>Screening image quality...</p>}
            {imageError && <p style={{ color: 'var(--red)', fontSize: '0.8rem', marginTop: '4px' }}>{imageError}</p>}
            {reportImagePreview && (
              <div style={{ marginTop: '10px' }}>
                <img src={reportImagePreview} alt="Incident Preview" style={{ maxHeight: '140px', borderRadius: '6px', border: '1px solid var(--panel-border)' }} />
                <span className="subtext" style={{ display: 'block', marginTop: '4px' }}>Attached: {reportImage?.name}</span>
              </div>
            )}
            {imageAnalysis && (
              <div style={{ marginTop: '8px', padding: '10px', background: 'var(--panel-bg)', borderRadius: '6px', border: '1px solid var(--panel-border)', fontSize: '0.82rem' }}>
                <div>Quality: <strong>{imageAnalysis.imageQuality}</strong> · Accepted: <strong>{imageAnalysis.imageAccepted ? 'YES' : 'NO'}</strong></div>
              </div>
            )}
          </div>
          <button
            className="btn-primary"
            disabled={reportSubmitting || !reportLocation.trim() || !reportDescription.trim()}
            onClick={submitReport}
          >
            {reportSubmitting ? 'Submitting…' : 'Submit Report'}
          </button>
        </div>
      )}

      {reportResult && (
        <div style={{ padding: '16px', borderRadius: '8px', background: 'var(--panel-subtle)', border: '1px solid var(--panel-border)', marginBottom: '20px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px' }}>Submission Status</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px', fontSize: '0.82rem' }}>
            <div>Status: <strong>{reportResult.verificationStatus || 'SUBMITTED'}</strong></div>
            <div>Image Quality: <strong>{reportResult.imageQuality || 'Screened'}</strong></div>
            <div>Severity: <strong>{reportResult.severity || 'UNKNOWN'}</strong></div>
          </div>
        </div>
      )}

      <div>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '12px' }}>Recent Reports ({submittedReports.length})</h4>
        {submittedReports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', background: 'var(--panel-subtle)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
            <p className="subtext">No field reports submitted in this session.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {submittedReports.map((report, idx) => (
              <div key={report.id || idx} style={{ padding: '12px 16px', background: 'var(--panel-subtle)', borderRadius: '6px', border: '1px solid var(--panel-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <strong style={{ fontSize: '0.88rem' }}>{report.location}</strong>
                  <span className="subtext">{new Date(report.timestamp || Date.now()).toLocaleTimeString()}</span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{report.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
