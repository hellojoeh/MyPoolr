-- Temporary RLS fix for production backend
-- This is a minimal, secure workaround until backend code is updated

-- Option 1: Create a temporary policy that allows service operations
-- This is more secure than full bypass
CREATE POLICY "Temporary service operations" ON mypoolr
    FOR ALL 
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Option 2: Alternative - Update existing policy to be more permissive for service role
-- Drop and recreate the insert policy
DROP POLICY IF EXISTS "Users can create MyPoolr groups" ON mypoolr;

CREATE POLICY "Users can create MyPoolr groups" ON mypoolr
    FOR INSERT WITH CHECK (
        -- Allow if user matches admin_id (normal user operation)
        admin_id = get_current_telegram_id() 
        OR 
        -- Allow service role operations (backend operations)
        current_setting('role') = 'service_role'
        OR
        -- Allow authenticated service operations
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
    );

-- Verify the policy
SELECT policyname, cmd, qual, with_check 
FROM pg_policies 
WHERE tablename = 'mypoolr' AND policyname LIKE '%create%';

-- Test that service_role can now insert
-- (This should work if you're connected as service_role)
-- SELECT current_user, current_setting('role', true);