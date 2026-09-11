export type District = {
  id: string
  state: string
  name: string
  lat: number
  lng: number
  riskScore: number | null
  status: string
  rain24h: number | null
  soilSat: number
  rainfall_3d?: number | null
  rainfall_7d?: number | null
  slopeAngle: number
  gsiEvents: number
  confidence: number
  modelSource: string
  factors: { name: string; weight: number; impact: number }[]
}

export type Corridor = { code: string; name: string; status: string; eta: string }
export type ForecastPoint = { timestamp: string; rainfall: number; riskScore: number; status: string; modelSource?: string }
export type RainfallData = { timestamp: string; rainfall_1h?: number; rainfall_24h?: number; rainfall_1d: number; rainfall_3d: number; rainfall_7d: number; source: string; is_live: boolean }
export type ImageAnalysis = { imageAccepted: boolean; imageQuality: string; verificationMode: string; imageAnalyzed?: boolean; verificationStatus: string; verificationConfidence: number; visualIndicators: string[]; descriptionMatch: boolean; classification: string; confidence: number; severity: string; objects: string[]; recommendedAction: string; modelSource: string; is_trained: boolean }
export type StateCoverage = {
  id: string
  name: string
  code: string
  boundary_available: boolean
  boundary_source: string
  geometry: any | null
  monitored_points_count: number
}

export type OperationalPoint = {
  id: string
  state_id: string
  name: string
  lat: number
  lng: number
  point_type: 'District Centroid' | 'Corridor Node' | 'High Pass' | 'Plateau'
  district_name: string
}

export type CoverageSummary = {
  coverage_configured: boolean
  total_states: number
  states_configured: number
  boundary_data_available: boolean
  states: StateCoverage[]
  operational_points: OperationalPoint[]
  source: string
  timestamp: string
}

export type RiskPrediction = {
  riskScore: number | null
  status: string
  severity: string
  confidence: number
  factors: { name: string; weight: number; impact: number }[]
  modelSource: string
}

export const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

export async function postJSON<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

export const fallbackDistricts: District[] = [
  { id: 'champhai', state: 'Mizoram', name: 'Champhai District', lat: 23.4756, lng: 93.3289, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 88, slopeAngle: 42, gsiEvents: 14, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'senapati', state: 'Manipur', name: 'Senapati NH-2 Corridor', lat: 25.2686, lng: 94.0186, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 85, slopeAngle: 44, gsiEvents: 16, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'cherrapunji', state: 'Meghalaya', name: 'Sohra / Cherrapunji Plateau', lat: 25.27, lng: 91.732, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 91, slopeAngle: 40, gsiEvents: 19, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'tawang', state: 'Arunachal Pradesh', name: 'Tawang High Pass', lat: 27.586, lng: 91.865, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 79, slopeAngle: 43, gsiEvents: 11, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'kohima', state: 'Nagaland', name: 'Kohima Bypass Corridor', lat: 25.6751, lng: 94.1086, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 82, slopeAngle: 41, gsiEvents: 13, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'dima_hasao', state: 'Assam', name: 'Dima Hasao Hill Axis', lat: 25.18, lng: 93.02, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 80, slopeAngle: 38, gsiEvents: 10, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'dhalai', state: 'Tripura', name: 'Dhalai Pass Corridor', lat: 23.84, lng: 91.28, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 76, slopeAngle: 35, gsiEvents: 7, confidence: 0, modelSource: 'uninitialized', factors: [] },
  { id: 'gangtok', state: 'Sikkim', name: 'Gangtok / East Sikkim', lat: 27.33, lng: 88.61, riskScore: 0, status: 'Pending', rain24h: 0, soilSat: 83, slopeAngle: 42, gsiEvents: 15, confidence: 0, modelSource: 'uninitialized', factors: [] },
]

export const fallbackCorridors: Corridor[] = [
  { code: 'NH-306', name: 'Silchar – Aizawl Axis', status: 'BLOCKED', eta: '4-6 Hours' },
  { code: 'NH-2', name: 'Dimapur – Imphal Hwy', status: 'BLOCKED', eta: '8-12 Hours' },
  { code: 'NH-10', name: 'Gangtok – Siliguri Axis', status: 'RESTRICTED', eta: 'Monitored 24/7' },
  { code: 'NH-6', name: 'Guwahati – Shillong Expressway', status: 'OPEN', eta: 'Normal' },
]
