-- Feature Toggle System Migration
-- Adds tables for dynamic feature toggles with country and group-based controls

-- Create feature toggle types
CREATE TYPE feature_scope AS ENUM ('global', 'country', 'group', 'user');
CREATE TYPE toggle_status AS ENUM ('enabled', 'disabled', 'testing');

-- Feature definitions table
CREATE TABLE feature_definition (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE CHECK (length(name) > 0),
    description TEXT NOT NULL CHECK (length(description) > 0),
    category VARCHAR(50) NOT NULL CHECK (length(category) > 0),
    default_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    requires_tier tier_level,
    regulatory_restricted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Country configuration table
CREATE TABLE country_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    country_code VARCHAR(2) NOT NULL UNIQUE CHECK (length(country_code) = 2),
    country_name VARCHAR(100) NOT NULL CHECK (length(country_name) > 0),
    currency_code VARCHAR(3) NOT NULL CHECK (length(currency_code) = 3),
    timezone VARCHAR(50) NOT NULL CHECK (length(timezone) > 0),
    locale VARCHAR(10) NOT NULL DEFAULT 'en_US',
    payment_providers JSONB DEFAULT '[]',
    regulatory_restrictions JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Feature toggles table
CREATE TABLE feature_toggle (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(100) NOT NULL REFERENCES feature_definition(name) ON DELETE CASCADE,
    scope feature_scope NOT NULL,
    scope_value VARCHAR(100), -- country_code, mypoolr_id, or telegram_id
    status toggle_status NOT NULL DEFAULT 'enabled',
    percentage_rollout INTEGER CHECK (percentage_rollout >= 0 AND percentage_rollout <= 100),
    conditions JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure unique combinations of feature + scope + scope_value
    UNIQUE(feature_name, scope, scope_value)
);

-- Feature usage tracking table
CREATE TABLE feature_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL, -- Telegram user ID
    mypoolr_id UUID REFERENCES mypoolr(id) ON DELETE CASCADE,
    country_code VARCHAR(2),
    usage_count INTEGER NOT NULL DEFAULT 1,
    first_used_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Unique constraint for aggregation
    UNIQUE(feature_name, user_id, mypoolr_id)
);

-- Performance indexes
CREATE INDEX idx_feature_definition_name ON feature_definition(name);
CREATE INDEX idx_feature_definition_category ON feature_definition(category);

CREATE INDEX idx_country_config_code ON country_config(country_code);
CREATE INDEX idx_country_config_active ON country_config(is_active);

CREATE INDEX idx_feature_toggle_feature ON feature_toggle(feature_name);
CREATE INDEX idx_feature_toggle_scope ON feature_toggle(scope, scope_value);
CREATE INDEX idx_feature_toggle_status ON feature_toggle(status);
CREATE INDEX idx_feature_toggle_expires ON feature_toggle(expires_at);

CREATE INDEX idx_feature_usage_feature ON feature_usage(feature_name);
CREATE INDEX idx_feature_usage_user ON feature_usage(user_id);
CREATE INDEX idx_feature_usage_country ON feature_usage(country_code);
CREATE INDEX idx_feature_usage_last_used ON feature_usage(last_used_at);

-- Apply updated_at triggers
CREATE TRIGGER update_feature_definition_updated_at BEFORE UPDATE ON feature_definition FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_country_config_updated_at BEFORE UPDATE ON country_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_feature_toggle_updated_at BEFORE UPDATE ON feature_toggle FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default feature definitions
INSERT INTO feature_definition (name, description, category, default_enabled, requires_tier, regulatory_restricted) VALUES
('payment_integration', 'Enable payment processing via M-Pesa and other providers', 'payments', FALSE, 'essential', TRUE),
('multi_group_creation', 'Allow users to create multiple MyPoolr groups', 'groups', FALSE, 'advanced', FALSE),
('advanced_notifications', 'Enhanced notification system with custom schedules', 'notifications', FALSE, 'advanced', FALSE),
('loan_system', 'Enable loan functionality within groups', 'financial', FALSE, 'extended', TRUE),
('analytics_dashboard', 'Detailed analytics and reporting features', 'analytics', FALSE, 'advanced', FALSE),
('custom_rotation_schedules', 'Allow custom rotation frequencies beyond daily/weekly/monthly', 'groups', FALSE, 'essential', FALSE),
('security_deposit_flexibility', 'Allow custom security deposit multipliers', 'financial', FALSE, 'advanced', TRUE),
('bulk_operations', 'Enable bulk member management and operations', 'management', FALSE, 'extended', FALSE),
('api_access', 'Provide API access for third-party integrations', 'integration', FALSE, 'extended', FALSE),
('white_label', 'White-label branding options', 'branding', FALSE, 'extended', FALSE);

-- Insert default country configurations
INSERT INTO country_config (country_code, country_name, currency_code, timezone, locale, payment_providers, regulatory_restrictions) VALUES
('KE', 'Kenya', 'KES', 'Africa/Nairobi', 'en_KE', '["mpesa"]', '{"max_group_size": 50, "requires_kyc": true}'),
('UG', 'Uganda', 'UGX', 'Africa/Kampala', 'en_UG', '["mtn_mobile_money"]', '{"max_group_size": 30, "requires_kyc": false}'),
('TZ', 'Tanzania', 'TZS', 'Africa/Dar_es_Salaam', 'sw_TZ', '["tigo_pesa", "airtel_money"]', '{"max_group_size": 40, "requires_kyc": true}'),
('NG', 'Nigeria', 'NGN', 'Africa/Lagos', 'en_NG', '["flutterwave", "paystack"]', '{"max_group_size": 100, "requires_kyc": true}'),
('US', 'United States', 'USD', 'America/New_York', 'en_US', '["stripe"]', '{"max_group_size": 20, "requires_kyc": true, "restricted_features": ["loan_system"]}');

-- Insert default feature toggles for Kenya (most permissive for initial rollout)
INSERT INTO feature_toggle (feature_name, scope, scope_value, status) VALUES
('payment_integration', 'country', 'KE', 'enabled'),
('multi_group_creation', 'country', 'KE', 'enabled'),
('advanced_notifications', 'country', 'KE', 'enabled'),
('custom_rotation_schedules', 'country', 'KE', 'enabled'),
('analytics_dashboard', 'country', 'KE', 'testing');

-- Insert restrictive toggles for US (compliance-focused)
INSERT INTO feature_toggle (feature_name, scope, scope_value, status) VALUES
('payment_integration', 'country', 'US', 'disabled'),
('loan_system', 'country', 'US', 'disabled'),
('security_deposit_flexibility', 'country', 'US', 'disabled');