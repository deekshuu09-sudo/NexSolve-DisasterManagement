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
              className={`layer-chip ${layer === 'Road corridors' || layer === 'Corridor Nodes' ? 'active' : ''}`}
              onClick={() => setLayer('Corridor Nodes')}
            >
              Corridor Nodes
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
              <li><strong>Road Corridors:</strong> MoRTH / NHAI corridor registry metadata for key arterial axes</li>
              <li><strong>Boundaries:</strong> Survey of India Official Administrative Boundary Database (ABDB)</li>
            </ul>
            <button className="popover-close" onClick={() => setMapInfoOpen(false)}>Close</button>
          </div>
        </div>
      )}

      {(layer === 'Road corridors' || layer === 'Corridor Nodes') && (
        <div className="corridor-layer-notice">
          <strong>MoRTH / NHAI Corridor Registry Active</strong> — Operational corridor nodes shown ({corridors.length} registered axes). Route line geometry is not available in the current dataset.
        </div>
      )}

      {layer === 'Rainfall' && (
        <div className="corridor-layer-notice">
          <strong>Precipitation Layer Active</strong> — Showing 24h peak accumulation (mm) across operational monitoring points.
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
            const isRainfallLayer = layer === 'Rainfall'
            const isCorridorLayer = layer === 'Road corridors' || layer === 'Corridor Nodes'

            let color = '#22c55e'
            let radius = 14

            if (isRainfallLayer) {
              const rain = district.rain24h
              color = rain != null ? '#3b82f6' : '#9ca3af'
              radius = 16
            } else if (isCorridorLayer) {
              color = '#38bdf8'
              radius = 16
            } else {
              const score = district.riskScore ?? 0
              const decisionLevel = district.decision?.riskLevel
              color = decisionLevel === 'RED' ? '#ef4444' : decisionLevel === 'ORANGE' ? '#f97316' : decisionLevel === 'YELLOW' ? '#eab308' : '#22c55e'
              radius = Math.max(12, Math.min(26, score / 3))
            }

            const weatherStatusText = district.rain24h != null
              ? (district.decision?.dataStatus || 'LIVE / STALE')
              : 'UNAVAILABLE'

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
                      {isRainfallLayer ? (
                        <>
                          <div><span>24h Rainfall:</span> <strong>{district.rain24h != null ? `${district.rain24h} mm` : 'Unavailable'}</strong></div>
                          <div><span>Weather Status:</span> <strong>{weatherStatusText}</strong></div>
                          <div><span>Slope Angle:</span> <strong>{district.slopeAngle ? `${district.slopeAngle.toFixed(1)}°` : 'N/A'}</strong></div>
                        </>
                      ) : (
                        <>
                          <div><span>Risk Score:</span> <strong>{district.riskScore != null ? district.riskScore : 'N/A'}</strong></div>
                          <div><span>24h Rainfall:</span> <strong>{district.rain24h != null ? `${district.rain24h} mm` : 'Unavailable'}</strong></div>
                          <div><span>Slope Angle:</span> <strong>{district.slopeAngle ? `${district.slopeAngle.toFixed(1)}°` : 'N/A'}</strong></div>
                          <div><span>Point Type:</span> <strong>{district.decision?.riskLabel || 'Operational Node'}</strong></div>
                        </>
                      )}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

        <div className="map-floating-legend">
          {layer === 'Rainfall' ? (
            <>
              <div className="legend-title">24h Rainfall (Precipitation)</div>
              <div className="legend-items">
                <span className="legend-badge blue">● Actual value shown per node</span>
                <span className="legend-badge gray">● Unavailable when feed offline</span>
              </div>
            </>
          ) : layer === 'Road corridors' || layer === 'Corridor Nodes' ? (
            <>
              <div className="legend-title">Corridor Registry</div>
              <div className="legend-items">
                <span className="legend-badge blue">● MoRTH Operational Node</span>
              </div>
            </>
          ) : (
            <>
              <div className="legend-title">Risk Level</div>
              <div className="legend-items">
                <span className="legend-badge red">■ Critical (&ge;75)</span>
                <span className="legend-badge orange">■ High (&ge;50)</span>
                <span className="legend-badge yellow">■ Elevated (&ge;35)</span>
                <span className="legend-badge green">■ Nominal (&lt;35)</span>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
