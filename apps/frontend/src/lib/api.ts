import axios from 'axios'

export interface InstantScrapeRequest {
  url: string
  extraction_type: 'css' | 'xpath' | 'ai'
  selectors?: Record<string, string>
  engine?: 'scrapy' | 'playwright'
  use_playwright?: boolean
  fields?: string[]
}

export interface ScheduledScrapeRequest extends InstantScrapeRequest {
  name: string
  frequency: 'minute' | 'hourly' | 'daily' | 'weekly' | 'monthly'
  cron_expression?: string
  search_type?: 'jobs' | 'flights' | 'generic'
  search_params?: Record<string, unknown>
}

export interface AIAnalyzeRequest {
  url: string
}

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Interceptor para JWT
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptor para 401 → redirect login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

// Scraper API
export const scraperApi = {
  instantScrape: (data: InstantScrapeRequest) =>
    api.post('/scrape/instant', data),
  scheduleScrape: (data: ScheduledScrapeRequest) =>
    api.post('/scrape/scheduled', data),
  getJobs: (params?: { status?: string; type?: string; page?: number; page_size?: number }) =>
    api.get('/scrape/jobs', { params }),
  getJob: (id: string) =>
    api.get(`/scrape/jobs/${id}`),
  pauseJob: (id: string) =>
    api.patch(`/scrape/jobs/${id}`, { status: 'paused' }),
  resumeJob: (id: string) =>
    api.patch(`/scrape/jobs/${id}`, { status: 'running' }),
  deleteJob: (id: string) =>
    api.delete(`/scrape/jobs/${id}`),
  getResults: (jobId: string, params?: { page?: number; limit?: number }) =>
    api.get(`/scrape/results/${jobId}`, { params }),
  analyzeWithAI: (url: string) =>
    api.post('/ai/analyze-page', { url }),
}

// AI API
export const aiApi = {
  getModels: () => api.get('/ai/models'),
  testModel: (modelId: string) => api.post('/ai/models/test', { model_id: modelId }),
  getUsageHistory: () => api.get('/ai/usage'),
  setPreferredModel: (modelId: string) =>
    api.post('/ai/models/preferred', { model_id: modelId }),
}

// Export API
export const exportApi = {
  exportCsv: (jobId: string) =>
    api.get(`/export/${jobId}/csv`, { responseType: 'blob' }),
  exportExcel: (jobId: string) =>
    api.get(`/export/${jobId}/excel`, { responseType: 'blob' }),
  exportJson: (jobId: string) =>
    api.get(`/export/${jobId}/json`, { responseType: 'blob' }),
}

// Search API (specialized)
export const searchApi = {
  searchFlights: (params: {
    origin: string
    destination: string
    departure_date: string
    return_date?: string
    passengers: number
    destination_country?: string
    destination_city?: string
    origin_city?: string
    date_flexibility_days?: number
  }) => api.post('/search/flights', params),

  searchNews: (params: {
    query: string
    sources?: string[]
    from_date?: string
    to_date?: string
  }) => api.post('/search/news', params),

  searchLeads: (params: {
    sector: string
    country: string
    target_role?: string
  }) => api.post('/search/leads', params),

  searchJobs: (params: {
    query: string
    location?: string
    contract_type?: string
  }) => api.post('/search/jobs', params),
}

// Dashboard API
export const dashboardApi = {
  getMetrics: () => api.get('/dashboard/metrics'),
  getJobsChart: (days?: number) =>
    api.get('/dashboard/jobs-chart', { params: { days: days || 7 } }),
  getRecentJobs: (limit?: number) =>
    api.get('/dashboard/recent-jobs', { params: { limit: limit || 10 } }),
  getServicesHealth: () => api.get('/dashboard/health'),
}
