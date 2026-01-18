-- Heracles PostgreSQL Initialization Script
-- ==========================================
-- This script creates all required tables for Heracles

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ===========================================
-- Audit Log Table
-- ===========================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Actor information
    actor_dn VARCHAR(512),
    actor_ip INET,
    actor_session_id VARCHAR(128),
    
    -- Action details
    action VARCHAR(50) NOT NULL,  -- CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    resource_type VARCHAR(50) NOT NULL,  -- user, group, system, etc.
    resource_dn VARCHAR(512),
    
    -- Change details
    changes JSONB,  -- {field: {old: ..., new: ...}}
    
    -- Request context
    request_id VARCHAR(128),
    user_agent TEXT,
    
    -- Status
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    
    -- Indexes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_actor_dn ON audit_logs(actor_dn);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_resource_dn ON audit_logs(resource_dn);
CREATE INDEX idx_audit_logs_success ON audit_logs(success);

-- ===========================================
-- Sessions Table
-- ===========================================
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(128) PRIMARY KEY,
    user_dn VARCHAR(512) NOT NULL,
    user_uid VARCHAR(64) NOT NULL,
    
    -- Session data
    data JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Security
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_sessions_user_dn ON sessions(user_dn);
CREATE INDEX idx_sessions_user_uid ON sessions(user_uid);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- ===========================================
-- Job Queue Table
-- ===========================================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Job definition
    job_type VARCHAR(50) NOT NULL,  -- ldap_sync, email_send, cleanup, etc.
    payload JSONB NOT NULL,
    
    -- Scheduling
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    
    -- Results
    result JSONB,
    error TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Priority (lower = higher priority)
    priority INTEGER NOT NULL DEFAULT 100
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_scheduled_at ON jobs(scheduled_at);
CREATE INDEX idx_jobs_job_type ON jobs(job_type);
CREATE INDEX idx_jobs_priority_scheduled ON jobs(priority, scheduled_at) WHERE status = 'pending';

-- ===========================================
-- Configuration Table
-- ===========================================
CREATE TABLE IF NOT EXISTS config (
    key VARCHAR(128) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(512)
);

-- Insert default configuration
INSERT INTO config (key, value, description) VALUES
    ('ldap.user_base', '"ou=people"', 'Base DN for user objects (relative to LDAP_BASE_DN)'),
    ('ldap.group_base', '"ou=groups"', 'Base DN for group objects'),
    ('ldap.system_base', '"ou=systems"', 'Base DN for system objects'),
    ('ldap.dns_base', '"ou=dns"', 'Base DN for DNS zones'),
    ('ldap.dhcp_base', '"ou=dhcp"', 'Base DN for DHCP configurations'),
    ('ldap.sudo_base', '"ou=sudoers"', 'Base DN for sudo rules'),
    ('auth.session_timeout', '3600', 'Session timeout in seconds'),
    ('auth.max_login_attempts', '5', 'Maximum failed login attempts before lockout'),
    ('auth.lockout_duration', '900', 'Account lockout duration in seconds'),
    ('password.default_hash', '"ssha"', 'Default password hash method'),
    ('password.min_length', '8', 'Minimum password length'),
    ('ui.items_per_page', '25', 'Default items per page in lists'),
    ('ui.theme', '"light"', 'Default UI theme')
ON CONFLICT (key) DO NOTHING;

-- ===========================================
-- Schema Migrations Table
-- ===========================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('001_initial');

-- ===========================================
-- Functions
-- ===========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_config_updated_at
    BEFORE UPDATE ON config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to archive old audit logs
CREATE OR REPLACE FUNCTION archive_old_audit_logs(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- In production, this would move to an archive table or external storage
    -- For now, we just delete old logs
    DELETE FROM audit_logs WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- Comments
-- ===========================================
COMMENT ON TABLE audit_logs IS 'Stores all audit events for compliance and debugging';
COMMENT ON TABLE sessions IS 'User session storage (primary storage in Redis, backup in PostgreSQL)';
COMMENT ON TABLE jobs IS 'Background job queue for async operations';
COMMENT ON TABLE config IS 'Application configuration stored in database';
