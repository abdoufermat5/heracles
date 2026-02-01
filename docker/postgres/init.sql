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
-- Configuration Categories Table
-- ===========================================
CREATE TABLE IF NOT EXISTS config_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,       -- e.g., 'general', 'ldap', 'security'
    label VARCHAR(100) NOT NULL,            -- Display name
    description TEXT,
    icon VARCHAR(50),                       -- Lucide icon name
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===========================================
-- Configuration Settings Table (Enhanced)
-- ===========================================
CREATE TABLE IF NOT EXISTS config_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID NOT NULL REFERENCES config_categories(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,              -- e.g., 'theme', 'language', 'session_timeout'
    value JSONB NOT NULL,                   -- Current value (typed JSON)
    default_value JSONB,                    -- Default value
    
    -- Metadata for UI rendering
    label VARCHAR(200) NOT NULL,            -- Display label
    description TEXT,                       -- Help text
    data_type VARCHAR(30) NOT NULL,         -- string, integer, boolean, list, select, etc.
    
    -- Validation rules
    validation_rules JSONB,                 -- {min: 1, max: 100, pattern: "...", required: true}
    options JSONB,                          -- For select fields: [{value: "a", label: "A"}]
    
    -- Behavior flags
    requires_restart BOOLEAN DEFAULT false,
    sensitive BOOLEAN DEFAULT false,        -- Mask in UI/logs
    read_only BOOLEAN DEFAULT false,        -- Cannot be changed via UI
    
    -- Grouping within category
    section VARCHAR(50),                    -- Sub-section within category
    display_order INTEGER DEFAULT 0,
    
    -- Dependencies for conditional display
    depends_on VARCHAR(100),                -- Key of another setting
    depends_on_value JSONB,                 -- Value condition
    
    -- Audit
    updated_by VARCHAR(512),                -- DN of last editor
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(category_id, key)
);

CREATE INDEX idx_config_settings_category ON config_settings(category_id);
CREATE INDEX idx_config_settings_key ON config_settings(key);

-- ===========================================
-- Plugin Configuration Table
-- ===========================================
CREATE TABLE IF NOT EXISTS plugin_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plugin_name VARCHAR(50) NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 50,
    
    -- Configuration stored as JSON
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Schema for validation (JSON Schema format)
    config_schema JSONB,
    
    -- Metadata
    version VARCHAR(20),
    description TEXT,
    
    -- Audit
    updated_by VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_plugin_configs_enabled ON plugin_configs(enabled);

-- ===========================================
-- Configuration History Table (Audit Trail)
-- ===========================================
CREATE TABLE IF NOT EXISTS config_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- What changed (one of these will be set)
    setting_id UUID REFERENCES config_settings(id) ON DELETE SET NULL,
    plugin_name VARCHAR(50),
    
    -- Category for global settings
    category VARCHAR(50),
    setting_key VARCHAR(100),
    
    -- Change details
    old_value JSONB,
    new_value JSONB,
    
    -- Who and when
    changed_by VARCHAR(512) NOT NULL,       -- DN or 'system'
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason TEXT,
    
    -- Request context
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_config_history_setting ON config_history(setting_id);
CREATE INDEX idx_config_history_plugin ON config_history(plugin_name);
CREATE INDEX idx_config_history_changed_at ON config_history(changed_at DESC);
CREATE INDEX idx_config_history_changed_by ON config_history(changed_by);

-- ===========================================
-- Legacy Configuration Table (for migration)
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

CREATE TRIGGER update_config_categories_updated_at
    BEFORE UPDATE ON config_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_config_settings_updated_at
    BEFORE UPDATE ON config_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plugin_configs_updated_at
    BEFORE UPDATE ON plugin_configs
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
COMMENT ON TABLE config IS 'Legacy application configuration (deprecated, use config_settings)';
COMMENT ON TABLE config_categories IS 'Configuration categories for organizing settings';
COMMENT ON TABLE config_settings IS 'Configuration settings with full metadata and validation';
COMMENT ON TABLE plugin_configs IS 'Plugin-specific configuration with JSON Schema validation';
COMMENT ON TABLE config_history IS 'Audit trail for all configuration changes';

-- ===========================================
-- Seed Data: Configuration Categories
-- ===========================================
INSERT INTO config_categories (name, label, description, icon, display_order) VALUES
    ('general', 'General', 'General application settings', 'settings', 10),
    ('ldap', 'LDAP', 'LDAP directory settings', 'server', 20),
    ('security', 'Security', 'Security and access control settings', 'shield', 30),
    ('password', 'Password Policy', 'Password requirements and hashing', 'key', 40),
    ('session', 'Sessions', 'Session management settings', 'clock', 50),
    ('audit', 'Audit & Logging', 'Audit trail and logging settings', 'file-text', 60),
    ('snapshots', 'Snapshots', 'Backup and snapshot settings', 'archive', 70)
ON CONFLICT (name) DO NOTHING;

-- ===========================================
-- Seed Data: General Settings
-- ===========================================
INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, options, display_order)
SELECT 
    c.id,
    s.key,
    s.value,
    s.default_value,
    s.label,
    s.description,
    s.data_type,
    s.options,
    s.display_order
FROM config_categories c
CROSS JOIN (VALUES
    ('language', '"en"', '"en"', 'Language', 'Default language for the interface', 'select', 
     '[{"value":"en","label":"English"},{"value":"fr","label":"Français"},{"value":"de","label":"Deutsch"}]'::jsonb, 10),
    ('timezone', '"UTC"', '"UTC"', 'Timezone', 'Default timezone for date/time display', 'string', NULL, 20),
    ('date_format', '"YYYY-MM-DD"', '"YYYY-MM-DD"', 'Date Format', 'Format for displaying dates', 'select',
     '[{"value":"YYYY-MM-DD","label":"2026-01-31"},{"value":"DD/MM/YYYY","label":"31/01/2026"},{"value":"MM/DD/YYYY","label":"01/31/2026"}]'::jsonb, 30),
    ('items_per_page', '25', '25', 'Items Per Page', 'Default number of items to show in lists', 'integer', NULL, 40),
    ('theme', '"system"', '"system"', 'Theme', 'Color theme for the interface', 'select',
     '[{"value":"light","label":"Light"},{"value":"dark","label":"Dark"},{"value":"system","label":"System"}]'::jsonb, 50)
) AS s(key, value, default_value, label, description, data_type, options, display_order)
WHERE c.name = 'general'
ON CONFLICT (category_id, key) DO NOTHING;

-- ===========================================
-- Seed Data: LDAP Settings
-- ===========================================
INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, section, display_order)
SELECT 
    c.id,
    s.key,
    s.value,
    s.default_value,
    s.label,
    s.description,
    s.data_type,
    s.section,
    s.display_order
FROM config_categories c
CROSS JOIN (VALUES
    ('user_rdn', '"ou=people"', '"ou=people"', 'User RDN', 'Relative DN for user objects', 'string', 'RDN Settings', 10),
    ('group_rdn', '"ou=groups"', '"ou=groups"', 'Group RDN', 'Relative DN for group objects', 'string', 'RDN Settings', 20),
    ('system_rdn', '"ou=systems"', '"ou=systems"', 'System RDN', 'Relative DN for system objects', 'string', 'RDN Settings', 30),
    ('dns_rdn', '"ou=dns"', '"ou=dns"', 'DNS RDN', 'Relative DN for DNS zones', 'string', 'RDN Settings', 40),
    ('dhcp_rdn', '"ou=dhcp"', '"ou=dhcp"', 'DHCP RDN', 'Relative DN for DHCP configuration', 'string', 'RDN Settings', 50),
    ('sudo_rdn', '"ou=sudoers"', '"ou=sudoers"', 'Sudo RDN', 'Relative DN for sudo rules', 'string', 'RDN Settings', 60),
    ('size_limit', '1000', '1000', 'Size Limit', 'Maximum number of entries to return in searches', 'integer', 'Search Limits', 70),
    ('time_limit', '30', '30', 'Time Limit', 'Maximum time in seconds for search operations', 'integer', 'Search Limits', 80)
) AS s(key, value, default_value, label, description, data_type, section, display_order)
WHERE c.name = 'ldap'
ON CONFLICT (category_id, key) DO NOTHING;

-- ===========================================
-- Seed Data: Password Policy Settings
-- ===========================================
INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, validation_rules, options, display_order)
SELECT 
    c.id,
    s.key,
    s.value,
    s.default_value,
    s.label,
    s.description,
    s.data_type,
    s.validation_rules,
    s.options,
    s.display_order
FROM config_categories c
CROSS JOIN (VALUES
    ('min_length', '8', '8', 'Minimum Length', 'Minimum password length', 'integer', 
     '{"min": 4, "max": 128}'::jsonb, NULL, 10),
    ('require_uppercase', 'true', 'true', 'Require Uppercase', 'Require at least one uppercase letter', 'boolean', NULL, NULL, 20),
    ('require_lowercase', 'true', 'true', 'Require Lowercase', 'Require at least one lowercase letter', 'boolean', NULL, NULL, 30),
    ('require_numbers', 'true', 'true', 'Require Numbers', 'Require at least one number', 'boolean', NULL, NULL, 40),
    ('require_special', 'false', 'false', 'Require Special Characters', 'Require at least one special character', 'boolean', NULL, NULL, 50),
    ('default_hash_method', '"ssha"', '"ssha"', 'Hash Method', 'Default password hashing algorithm', 'select', NULL,
     '[{"value":"ssha","label":"SSHA (Salted SHA-1)"},{"value":"ssha256","label":"SSHA256"},{"value":"ssha512","label":"SSHA512"},{"value":"argon2","label":"Argon2"}]'::jsonb, 60),
    ('expiration_days', '0', '0', 'Expiration Days', 'Days until password expires (0 = never)', 'integer',
     '{"min": 0, "max": 365}'::jsonb, NULL, 70)
) AS s(key, value, default_value, label, description, data_type, validation_rules, options, display_order)
WHERE c.name = 'password'
ON CONFLICT (category_id, key) DO NOTHING;

-- ===========================================
-- Seed Data: Session Settings
-- ===========================================
INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, validation_rules, display_order)
SELECT 
    c.id,
    s.key,
    s.value,
    s.default_value,
    s.label,
    s.description,
    s.data_type,
    s.validation_rules,
    s.display_order
FROM config_categories c
CROSS JOIN (VALUES
    ('session_timeout', '3600', '3600', 'Session Timeout', 'Session timeout in seconds', 'integer',
     '{"min": 300, "max": 86400}'::jsonb, 10),
    ('max_concurrent_sessions', '5', '5', 'Max Concurrent Sessions', 'Maximum concurrent sessions per user (0 = unlimited)', 'integer',
     '{"min": 0, "max": 100}'::jsonb, 20),
    ('idle_timeout', '1800', '1800', 'Idle Timeout', 'Idle timeout in seconds before auto-logout', 'integer',
     '{"min": 300, "max": 86400}'::jsonb, 30)
) AS s(key, value, default_value, label, description, data_type, validation_rules, display_order)
WHERE c.name = 'session'
ON CONFLICT (category_id, key) DO NOTHING;

-- ===========================================
-- Seed Data: Audit Settings
-- ===========================================
INSERT INTO config_settings (category_id, key, value, default_value, label, description, data_type, options, display_order)
SELECT 
    c.id,
    s.key,
    s.value,
    s.default_value,
    s.label,
    s.description,
    s.data_type,
    s.options,
    s.display_order
FROM config_categories c
CROSS JOIN (VALUES
    ('enable_audit_log', 'true', 'true', 'Enable Audit Log', 'Log all user actions', 'boolean', NULL, 10),
    ('log_level', '"INFO"', '"INFO"', 'Log Level', 'Application log level', 'select',
     '[{"value":"DEBUG","label":"Debug"},{"value":"INFO","label":"Info"},{"value":"WARNING","label":"Warning"},{"value":"ERROR","label":"Error"}]'::jsonb, 20),
    ('retention_days', '90', '90', 'Retention Days', 'Days to keep audit logs', 'integer', NULL, 30)
) AS s(key, value, default_value, label, description, data_type, options, display_order)
WHERE c.name = 'audit'
ON CONFLICT (category_id, key) DO NOTHING;
