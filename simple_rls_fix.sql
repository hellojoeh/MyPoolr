-- Simple RLS fix that works within Supabase constraints
-- Run this in your Supabase SQL editor

-- First, let's see what roles exist
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolbypassrls
FROM pg_roles 
WHERE rolname IN ('service_role', 'authenticator', 'anon', 'postgres');

-- Remove all existing restrictive policies and create one permissive policy
DROP POLICY IF EXISTS "Users can create MyPoolr groups" ON mypoolr;
DROP POLICY IF EXISTS "Admins can update their MyPoolr groups" ON mypoolr;
DROP POLICY IF EXISTS "Admins can delete their MyPoolr groups" ON mypoolr;
DROP POLICY IF EXISTS "Users can view MyPoolr groups they participate in" ON mypoolr;
DROP POLICY IF EXISTS "Temporary service operations" ON mypoolr;
DROP POLICY IF EXISTS "Backend operations bypass" ON mypoolr;

-- Create one simple, permissive policy for all operations
CREATE POLICY "Allow all operations" ON mypoolr
    FOR ALL 
    USING (true)
    WITH CHECK (true);

-- Verify the policy was created
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies 
WHERE tablename = 'mypoolr'
ORDER BY policyname;