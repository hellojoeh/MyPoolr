-- Feature Toggle Database Functions
-- Adds utility functions for feature toggle operations

-- Function to increment usage count
CREATE OR REPLACE FUNCTION increment_usage_count(usage_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE feature_usage 
    SET usage_count = usage_count + 1,
        last_used_at = NOW()
    WHERE id = usage_id;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired toggles
CREATE OR REPLACE FUNCTION cleanup_expired_toggles()
RETURNS integer AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM feature_toggle 
    WHERE expires_at IS NOT NULL 
    AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get feature status with context
CREATE OR REPLACE FUNCTION get_feature_status(
    p_feature_name VARCHAR(100),
    p_user_id BIGINT DEFAULT NULL,
    p_mypoolr_id UUID DEFAULT NULL,
    p_country_code VARCHAR(2) DEFAULT NULL
)
RETURNS TABLE(
    feature_name VARCHAR(100),
    status toggle_status,
    scope feature_scope,
    scope_value VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ft.feature_name,
        ft.status,
        ft.scope,
        ft.scope_value
    FROM feature_toggle ft
    WHERE ft.feature_name = p_feature_name
    AND (ft.expires_at IS NULL OR ft.expires_at > NOW())
    AND (
        (ft.scope = 'global') OR
        (ft.scope = 'user' AND ft.scope_value = p_user_id::VARCHAR) OR
        (ft.scope = 'group' AND ft.scope_value = p_mypoolr_id::VARCHAR) OR
        (ft.scope = 'country' AND ft.scope_value = p_country_code)
    )
    ORDER BY 
        CASE ft.scope
            WHEN 'user' THEN 1
            WHEN 'group' THEN 2
            WHEN 'country' THEN 3
            WHEN 'global' THEN 4
        END;
END;
$$ LANGUAGE plpgsql;

-- Function to get country restrictions
CREATE OR REPLACE FUNCTION get_country_restrictions(p_country_code VARCHAR(2))
RETURNS JSONB AS $$
DECLARE
    restrictions JSONB;
BEGIN
    SELECT regulatory_restrictions 
    INTO restrictions
    FROM country_config 
    WHERE country_code = p_country_code 
    AND is_active = true;
    
    RETURN COALESCE(restrictions, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- Function to check tier requirement
CREATE OR REPLACE FUNCTION check_tier_requirement(
    p_required_tier tier_level,
    p_user_tier tier_level
)
RETURNS BOOLEAN AS $$
DECLARE
    tier_hierarchy INTEGER[];
    required_index INTEGER;
    user_index INTEGER;
BEGIN
    -- Define tier hierarchy (starter=1, essential=2, advanced=3, extended=4)
    tier_hierarchy := ARRAY[1, 2, 3, 4];
    
    -- Get tier indices
    required_index := CASE p_required_tier
        WHEN 'starter' THEN 1
        WHEN 'essential' THEN 2
        WHEN 'advanced' THEN 3
        WHEN 'extended' THEN 4
        ELSE 1
    END;
    
    user_index := CASE p_user_tier
        WHEN 'starter' THEN 1
        WHEN 'essential' THEN 2
        WHEN 'advanced' THEN 3
        WHEN 'extended' THEN 4
        ELSE 1
    END;
    
    RETURN user_index >= required_index;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for the new functions
CREATE INDEX IF NOT EXISTS idx_feature_toggle_expires_cleanup ON feature_toggle(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_feature_usage_increment ON feature_usage(id, usage_count, last_used_at);