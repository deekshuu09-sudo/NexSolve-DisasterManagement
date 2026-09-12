export type RiskDecision = {
  alertId: string
  timestamp: string
  state: string
  district: string
  latitude: number
  longitude: number
  riskProbability: number | null
  riskLevel: 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED' | 'DATA_UNAVAILABLE'
  riskLabel: string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNAVAILABLE'
  dataStatus: string
  decisionStatus: string
  recommendedAction: string
  reasonCodes: string[]
  explanation: string
  modelId: string
  modelVersion: string
  featureSchemaVersion: string
  policyVersion: string
  isOfficialWarning: boolean
  disclaimer: string
}

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
  decision?: RiskDecision
}

export type Corridor = { code: string; name: string; status: string; eta: string }
export type ForecastPoint = { timestamp: string; rainfall: number; riskScore: number; status: string; modelSource?: string; decision?: RiskDecision }
export type RainfallData = { timestamp: string; rainfall_1h?: number; rainfall_24h?: number; rainfall_1d: number; rainfall_3d: number; rainfall_7d: number; source: string; is_live: boolean }
export type ImageAnalysis = { imageAccepted: boolean; imageQuality: string; verificationMode: string; imageAnalyzed?: boolean; verificationStatus: string; verificationConfidence: number; visualIndicators: string[]; descriptionMatch: boolean; classification: string; confidence: number; severity: string; objects: string[]; recommendedAction: string; modelSource: string; is_trained: boolean }
export type TerrainData = {
  available: boolean
  source: string
  elevation_m: number | null
  slope_deg: number | null
  aspect_deg: number | null
  curvature: number | null
  quality: string
}

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

export type DomainIndicator = {
  domain_name: string
  indicator: string
  raw_value: number | null
  normalized_score: number | null
  weight: number
  status: 'AVAILABLE' | 'UNAVAILABLE'
  source_dataset?: string
}

export type ContributingFactor = {
  domain_key: string
  domain_name: string
  indicator: string
  raw_value: number | null
  normalized_score: number | null
  weight: number
  contribution_pct: number
}

export type VulnerabilityProfile = {
  success: boolean
  district_id: string
  district_name_soi: string
  state_name: string
  dist_lgd: number | string | null
  status: 'COMPUTED' | 'PARTIAL' | 'INSUFFICIENT_DATA'
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNAVAILABLE'
  data_completeness_pct: number
  available_domains_count: number
  total_domains_count: number
  composite_vulnerability_score: number | null
  domains: Record<string, DomainIndicator>
  contributing_factors: ContributingFactor[]
  provenance: {
    domain?: string
    dataset_name?: string
    provider?: string
    reference_year?: string
  }[]
  disclaimer: string
}

export type ExposureRecord = {
  success: boolean
  district_id: string
  district_name_soi: string
  state_name: string
  dist_lgd: number | string | null
  status: 'AVAILABLE' | 'PARTIAL' | 'UNAVAILABLE'
  demographic?: {
    reference_year: string
    total_population_2011: number | null
    male_population: number | null
    female_population: number | null
    children_0_6: number | null
    scheduled_tribe_population: number | null
    scheduled_caste_population: number | null
    literate_population: number | null
    households: number | null
  } | null
  vulnerability?: {
    niti_mpi_reference_year: string
    headcount_ratio_pct: number | null
    intensity_poverty_pct: number | null
    mpi_score: number | null
    housing_deprived_pct: number | null
    sanitation_deprived_pct: number | null
    drinking_water_deprived_pct: number | null
    bmtpc_reference_year: string
    kutcha_wall_pct: number | null
    semi_pucca_wall_pct: number | null
    pucca_wall_pct: number | null
    landslide_hazard_zone: string | null
    earthquake_zone: string | null
  } | null
  healthcare?: {
    reference_year: string
    total_facilities: number | null
    district_hospitals: number | null
    chc_phc_subcenters: number | null
    total_bed_capacity: number | null
  } | null
  education?: {
    reference_year: string
    total_schools: number | null
    government_schools: number | null
    private_schools: number | null
    primary_schools: number | null
    secondary_schools: number | null
    higher_secondary_schools: number | null
    total_enrolment: number | null
  } | null
  transport?: {
    reference_year: string
    arterial_corridor_count: number | null
    arterial_highways: string[] | null
    arterial_highway_length_km: number | null
  } | null
  built_environment?: {
    reference_year: string
    source: string
    built_up_area_sqkm: number | null
    status: string
  } | null
  availability: Record<string, string>
  provenance: {
    domain: string
    dataset_name: string
    provider: string
    reference_year: string
    authoritative_tier: string
  }[]
  vulnerability_intelligence?: VulnerabilityProfile
}

export type HumanVerificationItem = {
  item_id: string
  label: string
  description: string
  category: string
}

export type UncertaintySection = {
  uncertainty_level: 'HIGH' | 'MEDIUM' | 'LOW'
  uncertainty_notes: string[]
  data_limitations: string
  model_limitations: string
}

export type ExplainabilityReport = {
  risk_probability: number | null
  risk_level: string
  confidence: string
  model_version: string
  model_id: string
  feature_schema_version: string
  weather_status: 'LIVE' | 'STALE' | 'HISTORICAL' | 'UNAVAILABLE'
  weather_source: string
  weather_timestamp?: string | null
  feature_values: Record<string, number | string | null>
  model_feature_importance: Record<string, number>
  local_explanation: {
    local_explanation_available: boolean
    rationale: string
    note: string
  }
  contributing_factors: {
    feature: string
    value_display: string
    global_importance: number
    description: string
  }[]
  reason_codes: string[]
  explanation_text: string
  uncertainty: UncertaintySection
  recommended_action: string
  human_verification_items: HumanVerificationItem[]
  vulnerability_context: {
    status: string
    confidence: string
    data_completeness_pct: number
    composite_vulnerability_score: number | null
    display_message: string
    contributing_factors: any[]
    decoupling_rule: string
  }
  is_official_warning: boolean
  disclaimer: string
}

export type RiskPrediction = {
  riskScore: number | null
  status: string
  severity: string
  confidence: number
  factors: { name: string; weight: number; impact: number }[]
  modelSource: string
  modelVersion?: string
  modelId?: string
  featureSchemaVersion?: string
  decision?: RiskDecision
  explainability?: ExplainabilityReport
}

export const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

export async function getExposure(districtId: string): Promise<ExposureRecord> {
  return getJSON<ExposureRecord>(`/api/exposure/${districtId}`)
}

export async function getVulnerabilityProfile(districtId: string): Promise<VulnerabilityProfile> {
  return getJSON<VulnerabilityProfile>(`/api/vulnerability/${districtId}`)
}

export type DashboardSummary = {
  success: boolean
  generated_at: string
  system_status: string
  spatial_framework: string
  monitored_districts_count: number
  operational_nodes_count: number
  weather_feed_health: {
    status: 'LIVE' | 'STALE' | 'UNAVAILABLE'
    live_points: number
    stale_points: number
    offline_points: number
  }
  risk_level_counts: Record<string, number>
  vulnerability_coverage_summary: {
    total_districts: number
    computed_count: number
    partial_count: number
    insufficient_data_count: number
  }
  corridors: Corridor[]
  operational_nodes: {
    id: string
    name: string
    state: string
    lat: number
    lng: number
    point_type: string
    riskScore: number | null
    status: string
    decision: RiskDecision
    vulnerability?: VulnerabilityProfile
  }[]
  disclaimer: string
}

export async function getExplainability(districtId: string): Promise<{ success: boolean; district_id: string; district_name: string; state: string; explainability: ExplainabilityReport }> {
  return getJSON(`/api/explainability/${districtId}`)
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return getJSON<DashboardSummary>('/api/dashboard/summary')
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
