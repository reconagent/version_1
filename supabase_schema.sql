-- Supabase schema for AETHERIC
CREATE TABLE findings (
    id BIGSERIAL PRIMARY KEY,
    source_ip TEXT NOT NULL,
    file_path TEXT NOT NULL,
    matched_regex TEXT,
    encrypted_content TEXT,
    confidence_score FLOAT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE targets (
    id BIGSERIAL PRIMARY KEY,
    ip TEXT NOT NULL,
    ports JSONB,
    status TEXT DEFAULT 'pending',
    discovered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    command_ran TEXT,
    exit_code INT,
    human_readable_desc TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE compromised_hosts (
    id BIGSERIAL PRIMARY KEY,
    ip TEXT NOT NULL,
    status TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE exploit_results (
    id BIGSERIAL PRIMARY KEY,
    target_ip TEXT,
    exploit_name TEXT,
    success BOOLEAN,
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_findings_ip ON findings(source_ip);
CREATE INDEX idx_targets_ip ON targets(ip);
CREATE INDEX idx_compromised_ip ON compromised_hosts(ip);
