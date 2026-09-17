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
          <h2>FIELD REPORTS</h2>
          <p className="subtext">
            Operational field observation submission & image quality screening portal
          </p>
        </div>
        <button className="primary-button" onClick={() => setReportOpen(!reportOpen)}>
          {reportOpen ? 'Close Form' : '+ Submit Field Incident'}
        </button>
      </div>

      {reportOpen && (
        <div className="report-form-container">
          <h3>Submit Field Observation Report</h3>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="field-report-location">Location / Corridor Axis *</label>
              <input
                id="field-report-location"
                type="text"
                value={reportLocation}
                onChange={(e) => setReportLocation(e.target.value)}
                placeholder="e.g. NH-306 Corridor, Champhai Axis"
              />
            </div>
            <div className="form-group inline-coords">
              <div>
                <label htmlFor="field-report-latitude">Latitude (Optional)</label>
                <input
                  id="field-report-latitude"
                  type="text"
                  value={reportLatitude}
                  onChange={(e) => setReportLatitude(e.target.value)}
                  placeholder="23.4756"
                />
              </div>
              <div>
                <label htmlFor="field-report-longitude">Longitude (Optional)</label>
                <input
                  id="field-report-longitude"
                  type="text"
                  value={reportLongitude}
                  onChange={(e) => setReportLongitude(e.target.value)}
                  placeholder="93.3289"
                />
              </div>
            </div>
            <div className="form-group full-width">
              <label htmlFor="field-report-description">Field Observations & Description *</label>
              <textarea
                id="field-report-description"
                rows={3}
                value={reportDescription}
                onChange={(e) => setReportDescription(e.target.value)}
                placeholder="Describe slope movement, road blockages, mud accumulation, or structural impacts..."
              />
            </div>
            <div className="form-group full-width">
              <label htmlFor="field-report-image">Incident Photograph (Image Quality Screening)</label>
              <input id="field-report-image" type="file" accept="image/*" onChange={handleImageChange} />
              {imageLoading && <p className="status-text">Analyzing image quality & resolution...</p>}
              {imageError && <p className="error-text">{imageError}</p>}
              {reportImagePreview && (
                <div className="image-preview-wrapper">
                  <img src={reportImagePreview} alt="Incident Upload Preview" className="uploaded-preview-img" />
                </div>
              )}
              {imageAnalysis && (
                <div className="image-analysis-badge-card">
                  <div className="analysis-title">AI-Assisted Image Screening Result</div>
                  <div>Quality: <strong>{imageAnalysis.imageQuality}</strong></div>
                  <div>Content Category: <strong>{imageAnalysis.contentCategory || 'Photo'}</strong></div>
                  <div>Accepted: <strong>{imageAnalysis.imageAccepted ? 'YES' : 'NO'}</strong></div>
                  <p className="note-text">
                    Note: Image quality screening checks exposure and focus. Landslide classification requires a validated vision model.
                  </p>
                </div>
              )}
            </div>
          </div>
          <div className="form-actions">
            <button
              className="submit-button"
              disabled={reportSubmitting || !reportLocation.trim() || !reportDescription.trim()}
              onClick={submitReport}
            >
              {reportSubmitting ? 'Submitting Report…' : 'Submit Field Report'}
            </button>
          </div>
        </div>
      )}

      {reportResult && (
        <div className="report-result-card">
          <h4>Report Submission Result</h4>
          <div className="result-grid">
            <div><span>Status:</span> <strong>{reportResult.verificationStatus || 'SUBMITTED'}</strong></div>
            <div><span>Image:</span> <strong>{reportImage ? 'RECEIVED' : 'NOT PROVIDED'}</strong></div>
            <div><span>Image Quality:</span> <strong>{reportResult.imageQuality || 'Screened'}</strong></div>
            <div><span>Landslide Classification:</span> <strong>{reportResult.landslideClassification || 'NOT AVAILABLE'}</strong></div>
            <div><span>Confidence:</span> <strong>{reportResult.verificationConfidence != null ? `${(reportResult.verificationConfidence * 100).toFixed(0)}%` : 'N/A'}</strong></div>
            <div><span>Severity:</span> <strong>{reportResult.severity || 'UNKNOWN'}</strong></div>
          </div>
          <div className="result-action">
            <strong>Recommended Response:</strong> {reportResult.recommendedAction || 'Record filed in operational log.'}
          </div>
        </div>
      )}

      <div className="submitted-feed">
        <h4>Recent Field Reports ({submittedReports.length})</h4>
        {submittedReports.length === 0 ? (
          <div className="empty-reports-panel">
            <div className="empty-panel-icon">📝</div>
            <div className="empty-panel-title">No field reports yet</div>
            <p className="empty-panel-desc">
              Submit a field observation with location, description, and optional image evidence using the button above.
            </p>
            <span className="empty-panel-sub">Reports submitted during this session will appear here.</span>
          </div>
        ) : (
          <div className="reports-list">
            {submittedReports.map((report, idx) => (
              <div key={report.id || idx} className="report-item-card">
                <div className="report-header">
                  <strong>{report.location}</strong>
                  <span className="report-time">{new Date(report.timestamp || Date.now()).toLocaleTimeString()}</span>
                </div>
                <p className="report-desc">{report.description}</p>
                <div className="report-tags">
                  <span className="tag">Quality: {report.imageQuality || 'Screened'}</span>
                  <span className="tag">Classification: {report.landslideClassification || 'NOT AVAILABLE'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
