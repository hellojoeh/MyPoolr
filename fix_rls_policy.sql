-- Fix RLS policy to allow service role operations
-- Run this in your Supabase SQL editor

-- First, let's check the current service role configuration
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'service_role';

-- Grant bypass RLS to service_role if it exists
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
        ALTER ROLE service_role BYPASSRLS;
        RAISE NOTICE 'Granted BYPASSRLS to service_role';
    ELSE
        RAISE NOTICE 'service_role does not exist';
    END IF;
END $$;

-- Alternative: Create a more permissive policy for backend operations
-- This allows insertions when the admin_id matches the record being inserted
DROP POLICY IF EXISTS "Users can create MyPoolr groups" ON mypoolr;

CREATE POLICY "Users can create MyPoolr groups" ON mypoolr
    FOR INSERT WITH CHECK (
        admin_id = get_current_telegram_id() OR
        current_user = 'service_role' OR
        current_user = 'postgres'
    );

-- Also update the other policies to be more permissive for service operations
DROP POLICY IF EXISTS "Admins can update their MyPoolr groups" ON mypoolr;
CREATE POLICY "Admins can update their MyPoolr groups" ON mypoolr
    FOR UPDATE USING (
        admin_id = get_current_telegram_id() OR
        current_user = 'service_role' OR
        current_user = 'postgres'
    ) WITH CHECK (
        admin_id = get_current_telegram_id() OR
        current_user = 'service_role' OR
        current_user = 'postgres'
    );

-- Verify the changes
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'mypoolr' AND policyname LIKE '%create%';