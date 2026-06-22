-- Migration 001: Initial Schema
-- WebScrapy AI Platform

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scraping Jobs
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    job_type VARCHAR(50) NOT NULL DEFAULT 'instant', -- instant, scheduled
    status VARCHAR(50) NOT NULL DEFAULT 'pending',   -- pending, running, completed, failed, paused
    config JSONB DEFAULT '{}',                        -- selectors, use_playwright, timeout, etc.
    search_type VARCHAR(50) DEFAULT 'generic',        -- generic, flights, news, leads, jobs
    search_params JSONB DEFAULT '{}',
    use_ai BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scraping Schedules
CREATE TABLE IF NOT EXISTS scraping_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    cron_expression VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    is_active BOOLEAN DEFAULT TRUE,
    next_run TIMESTAMPTZ,
    last_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scraping Runs
CREATE TABLE IF NOT EXISTS scraping_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    items_count INTEGER DEFAULT 0,
    error_message TEXT,
    method VARCHAR(50),         -- scrapy, playwright, api
    model_used VARCHAR(100),    -- NVIDIA model usado
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scraping Results
CREATE TABLE IF NOT EXISTS scraping_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES scraping_runs(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    raw_data JSONB NOT NULL DEFAULT '[]',
    structured_data JSONB DEFAULT '[]',
    quality_score INTEGER DEFAULT 0,
    quality_issues JSONB DEFAULT '[]',
    items_count INTEGER DEFAULT 0,
    storage_path TEXT,      -- MinIO path para dados grandes
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Public API Catalog (from public-apis repository)
CREATE TABLE IF NOT EXISTS public_api_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    auth_required BOOLEAN DEFAULT FALSE,
    auth_type VARCHAR(50),      -- apiKey, OAuth, No
    https_only BOOLEAN DEFAULT TRUE,
    cors_supported BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    search_types VARCHAR[] DEFAULT '{}',  -- flights, news, jobs, leads, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scraper Versions (for auto-healing)
CREATE TABLE IF NOT EXISTS scraper_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES scraping_jobs(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    code TEXT NOT NULL,
    selectors JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    reason TEXT,    -- 'manual', 'auto-healed', 'ai-generated'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_scraping_jobs_user_id ON scraping_jobs(user_id);
CREATE INDEX idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX idx_scraping_runs_job_id ON scraping_runs(job_id);
CREATE INDEX idx_scraping_runs_status ON scraping_runs(status);
CREATE INDEX idx_scraping_results_run_id ON scraping_results(run_id);
CREATE INDEX idx_scraping_results_job_id ON scraping_results(job_id);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_public_api_catalog_category ON public_api_catalog(category);

-- Seed: APIs públicas conhecidas para casos de uso do usuário
INSERT INTO public_api_catalog (name, description, url, category, auth_required, auth_type, search_types) VALUES
('NewsAPI', 'Agregador de notícias de centenas de fontes', 'https://newsapi.org/', 'News', TRUE, 'apiKey', ARRAY['news']),
('GNews', 'API de notícias globais', 'https://gnews.io/', 'News', TRUE, 'apiKey', ARRAY['news']),
('The News API', 'API de notícias em tempo real', 'https://www.thenewsapi.com/', 'News', TRUE, 'apiKey', ARRAY['news']),
('Mediastack', 'API de notícias globais gratuita', 'https://mediastack.com/', 'News', TRUE, 'apiKey', ARRAY['news']),
('Aviationstack', 'Dados de voos em tempo real', 'https://aviationstack.com/', 'Transportation', TRUE, 'apiKey', ARRAY['flights']),
('Amadeus', 'Dados de viagens e passagens', 'https://developers.amadeus.com/', 'Transportation', TRUE, 'apiKey', ARRAY['flights']),
('Arbeitnow', 'Vagas de emprego internacionais (grátis)', 'https://www.arbeitnow.com/api/job-board-api', 'Jobs', FALSE, 'No', ARRAY['jobs']),
('The Muse API', 'Vagas e cultura de empresas (grátis)', 'https://www.themuse.com/developers/api/v2', 'Jobs', FALSE, 'No', ARRAY['jobs']),
('Jooble', 'Agregador de vagas de emprego', 'https://jooble.org/api/about', 'Jobs', TRUE, 'apiKey', ARRAY['jobs']),
('Hunter.io', 'Busca e verificação de emails profissionais', 'https://hunter.io/api', 'Business', TRUE, 'apiKey', ARRAY['leads']);
