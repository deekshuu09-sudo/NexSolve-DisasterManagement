import { useEffect } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { District, Corridor } from '../lib/api'

function FitDistrictBounds({ districts }: { districts: District[] }) {
  const map = useMap()
  useEffect(() => {
    if (districts.length) {
      map.fitBounds(districts.map((district) => [district.lat, district.lng] as [number, number]), { padding: [24, 24] })
    }
  }, [districts, map])
  return null
}

type RiskMapProps = {
  districts: District[]
  corridors: Corridor[]
  selectedDistrictId: string | null
  setSelectedDistrictId: (id: string) => void
  layer: string
  setLayer: (layer: string) => void
  mapInfoOpen: boolean
  setMapInfoOpen: (open: boolean) => void
}

export default function RiskMap({
  districts,
  corridors,
  selectedDistrictId,
  setSelectedDistrictId,
  layer,
  setLayer,
  mapInfoOpen,
  setMapInfoOpen,
}: RiskMapProps) {
  return (
    <section id="map-step" className="step-card map-layout-card">
      <div className="section-header map-header">
        <div>
          <h2>Risk Map & Spatial Monitoring</h2>
          <p className="subtext">
            Authoritative Survey of India administrative centroids and corridor nodes for Northeast India
          </p>
        </div>
        <div className="map-actions">
          <div className="map-layer-selector">
            <span className="layer-label">Layers:</span>
            <button
              className={`layer-chip ${layer === 'Risk' || layer === 'All Layers' ? 'active' : ''}`}
              onClick={() => setLayer('Risk')}
            >
              Risk
            </button>
            <button
              className={`layer-chip ${layer === 'Rainfall' ? 'active' : ''}`}
              onClick={() => setLayer('Rainfall')}
            >
              Rainfall
            </button>
            <button
              className={`layer-chip ${layer === 'Road corridors' ? 'active' : ''}`}
              onClick={() => setLayer('Road corridors')}
            >
              Road corridors
            </button>
          </div>
          <button className="info-popover-trigger" onClick={() => setMapInfoOpen(!mapInfoOpen)}>
            ⓘ Map information
          </button>
        </div>
      </div>

      {mapInfoOpen && (
        <div className="map-info-popover">
          <div className="popover-content">
            <h4>Survey of India Map Standards & Provenance</h4>
            <p>
              Administrative boundaries and operational centroids are aligned with official Survey of India (SoI) standards.
              Elevation and slope indicators are computed using USGS NASADEM 1 Arc-Second (~30m SRTM DEM) data.
            </p>
            <ul>
              <li><strong>Basemap:</strong> OpenStreetMap Carto (Standard OSM EPSG:3857 tile services)</li>
              <li><strong>Road Corridors:</strong> MoRTH / NHAI registry metadata for key arterial axes</li>
              <li><strong>Boundaries:</strong> Survey of India Official Administrative Boundary Database (ABDB)</li>
            </ul>
            <button className="popover-close" onClick={() => setMapInfoOpen(false)}>Close</button>
          </div>
        </div>
      )}

      {layer === 'Road corridors' && (
        <div className="corridor-layer-notice">
          <strong>MoRTH / NHAI Corridor Registry Layer Active</strong> — Highlighting key arterial corridor nodes ({corridors.length} registered axes). Vector line geometry is not connected.
        </div>
      )}

      <div className="map-container-wrapper">
        <MapContainer center={[25.5, 92.5]} zoom={6} scrollWheelZoom={false} className="leaflet-map-element">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitDistrictBounds districts={districts} />
          {districts.map((district) => {
            const score = district.riskScore ?? 0
            const decisionLevel = district.decision?.riskLevel
            const color = decisionLevel === 'RED' ? '#ef4444' : decisionLevel === 'ORANGE' ? '#f97316' : decisionLevel === 'YELLOW' ? '#eab308' : '#22c55e'
            const radius = Math.max(12, Math.min(26, score / 3))

            return (
              <CircleMarker
                key={district.id}
                center={[district.lat, district.lng]}
                radius={radius}
                pathOptions={{ color, fillColor: color, fillOpacity: selectedDistrictId === district.id ? 0.9 : 0.6, weight: selectedDistrictId === district.id ? 3 : 1.5 }}
                eventHandlers={{
                  click: () => setSelectedDistrictId(district.id),
                }}
              >
                <Popup>
                  <div className="map-popup-card">
                    <h4>{district.name}</h4>
                    <p className="popup-state">{district.state}</p>
                    <div className="popup-metrics">
                      <div><span>Risk Score:</span> <strong>{district.riskScore != null ? district.riskScore : 'N/A'}</strong></div>
                      <div><span>24h Rainfall:</span> <strong>{district.rain24h != null ? `${district.rain24h} mm` : 'N/A'}</strong></div>
                      <div><span>Slope Angle:</span> <strong>{district.slopeAngle.toFixed(1)}°</strong></div>
                      <div><span>Model:</span> <strong>{district.modelSource}</strong></div>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

        <div className="map-floating-legend">
          <div className="legend-title">Risk Level</div>
          <div className="legend-items">
            <span className="legend-badge red">■ Critical (&ge;75)</span>
            <span className="legend-badge orange">■ High (&ge;50)</span>
            <span className="legend-badge yellow">■ Elevated (&ge;35)</span>
            <span className="legend-badge green">■ Nominal (&lt;35)</span>
          </div>
        </div>
      </div>
    </section>
  )
}
