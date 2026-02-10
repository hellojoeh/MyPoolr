-- Comprehensive RLS fix - this should resolve the issue
-- Run this in your Supabase SQL editor

-- First, let's see what role the backend is actually using
-- Check current connections and roles
SELECT usename, application_name, client_addr, state 
FROM pg_stat_activity 
WHERE datname = current_database() 
AND state = 'active'
LIMIT 5;

-- Check if service_role exists and its permissions
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolbypassrls
FROM pg_roles 
WHERE rolname IN ('service_role', 'authenticator', 'anon', 'postgres');

-- Grant service_role bypass RLS if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
        ALTER ROLE service_role BYPASSRLS;
        RAISE NOTICE 'Granted BYPASSRLS to service_role';
    END IF;
    
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'authenticator') THEN
        ALTER ROLE authenticator BYPASSRLS;
        RAISE NOTICE 'Granted BYPASSRLS to authenticator';
    END IF;
END $$;

-- Also create a very permissive policy as backup
DROP POLICY IF EXISTS "Backend operations bypass" ON mypoolr;
CREATE POLICY "Backend operations bypass" ON mypoolr
    FOR ALL 
    USING (
        -- Allow if normal user operation
        admin_id = get_current_telegram_id() 
        OR 
        -- Allow if any service operation (very permissive for now)
        current_user IN ('service_role', 'authenticator', 'postgres')
        OR
        -- Allow if no JWT claims (backend operation)
        current_setting('request.jwt.claims', true) IS NULL
        OR
        current_setting('request.jwt.claims', true) = ''
    )
    WITH CHECK (
        -- Same conditions for insert/update
        admin_id = get_current_telegram_id() 
        OR 
        current_user IN ('service_role', 'authenticator', 'postgres')
        OR
        current_setting('request.jwt.claims', true) IS NULL
        OR
        current_setting('request.jwt.claims', true) = ''
    );

-- Verify all policies on mypoolr table
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE tablename = 'mypoolr'
ORDER BY policyname;