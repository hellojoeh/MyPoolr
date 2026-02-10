-- Secure RLS solution for backend operations
-- This maintains security while allowing legitimate backend operations

-- 1. Create a secure function for MyPoolr creation that validates the operation
CREATE OR REPLACE FUNCTION create_mypoolr_secure(
    p_name VARCHAR(100),
    p_admin_id BIGINT,
    p_contribution_amount DECIMAL(15,2),
    p_rotation_frequency rotation_frequency,
    p_member_limit INTEGER,
    p_tier tier_level DEFAULT 'starter',
    p_country VARCHAR(2) DEFAULT 'KE'
)
RETURNS TABLE(
    id UUID,
    name VARCHAR(100),
    admin_id BIGINT,
    contribution_amount DECIMAL(15,2),
    rotation_frequency rotation_frequency,
    member_limit INTEGER,
    tier tier_level,
    country VARCHAR(2),
    status mypoolr_status,
    created_at TIMESTAMP WITH TIME ZONE
)
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validate input parameters
    IF p_name IS NULL OR length(trim(p_name)) = 0 THEN
        RAISE EXCEPTION 'Name cannot be empty';
    END IF;
    
    IF p_admin_id IS NULL OR p_admin_id <= 0 THEN
        RAISE EXCEPTION 'Invalid admin_id';
    END IF;
    
    IF p_contribution_amount IS NULL OR p_contribution_amount <= 0 THEN
        RAISE EXCEPTION 'Contribution amount must be greater than 0';
    END IF;
    
    IF p_member_limit IS NULL OR p_member_limit < 2 OR p_member_limit > 100 THEN
        RAISE EXCEPTION 'Member limit must be between 2 and 100';
    END IF;
    
    IF p_country IS NULL OR length(p_country) != 2 THEN
        RAISE EXCEPTION 'Country must be a 2-character code';
    END IF;
    
    -- Insert the record (this function runs with elevated privileges)
    RETURN QUERY
    INSERT INTO mypoolr (
        name, 
        admin_id, 
        contribution_amount, 
        rotation_frequency, 
        member_limit, 
        tier, 
        country,
        status,
        created_at
    ) VALUES (
        trim(p_name),
        p_admin_id,
        p_contribution_amount,
        p_rotation_frequency,
        p_member_limit,
        p_tier,
        upper(p_country),
        'active',
        NOW()
    )
    RETURNING 
        mypoolr.id,
        mypoolr.name,
        mypoolr.admin_id,
        mypoolr.contribution_amount,
        mypoolr.rotation_frequency,
        mypoolr.member_limit,
        mypoolr.tier,
        mypoolr.country,
        mypoolr.status,
        mypoolr.created_at;
END;
$$;

-- 2. Grant execute permission to service_role
GRANT EXECUTE ON FUNCTION create_mypoolr_secure TO service_role;

-- 3. Create audit logging for the function
CREATE OR REPLACE FUNCTION log_mypoolr_creation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Log the creation (you can extend this to write to an audit table)
    RAISE NOTICE 'MyPoolr created: ID=%, Name=%, Admin=%, Country=%', 
        NEW.id, NEW.name, NEW.admin_id, NEW.country;
    RETURN NEW;
END;
$$;

-- 4. Create trigger for audit logging
DROP TRIGGER IF EXISTS trigger_log_mypoolr_creation ON mypoolr;
CREATE TRIGGER trigger_log_mypoolr_creation
    AFTER INSERT ON mypoolr
    FOR EACH ROW
    EXECUTE FUNCTION log_mypoolr_creation();

-- 5. Keep the original RLS policies intact (no bypass)
-- The RLS policies remain as they were - secure by default

-- 6. Test the function
SELECT * FROM create_mypoolr_secure(
    'Test Secure Group',
    123456789,
    1000.00,
    'monthly',
    5,
    'starter',
    'KE'
);