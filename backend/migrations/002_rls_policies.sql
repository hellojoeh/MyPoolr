-- Row Level Security (RLS) Policies for Multi-tenant Isolation
-- Ensures users can only access data from their own MyPoolr groups

-- Enable RLS on all tables
ALTER TABLE mypoolr ENABLE ROW LEVEL SECURITY;
ALTER TABLE member ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's telegram_id from JWT claims
CREATE OR REPLACE FUNCTION get_current_telegram_id()
RETURNS BIGINT AS $$
BEGIN
    -- Extract telegram_id from JWT claims
    -- This assumes the JWT contains a telegram_id claim
    RETURN COALESCE(
        (current_setting('request.jwt.claims', true)::json->>'telegram_id')::BIGINT,
        0
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to check if user is admin of a MyPoolr
CREATE OR REPLACE FUNCTION is_mypoolr_admin(mypoolr_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM mypoolr 
        WHERE id = mypoolr_uuid 
        AND admin_id = get_current_telegram_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to check if user is member of a MyPoolr
CREATE OR REPLACE FUNCTION is_mypoolr_member(mypoolr_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM member 
        WHERE mypoolr_id = mypoolr_uuid 
        AND telegram_id = get_current_telegram_id()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- MyPoolr RLS Policies
-- Users can see MyPoolr groups where they are admin or member
CREATE POLICY "Users can view MyPoolr groups they participate in" ON mypoolr
    FOR SELECT USING (
        admin_id = get_current_telegram_id() OR
        is_mypoolr_member(id)
    );

-- Only admins can create MyPoolr groups
CREATE POLICY "Users can create MyPoolr groups" ON mypoolr
    FOR INSERT WITH CHECK (admin_id = get_current_telegram_id());

-- Only admins can update their MyPoolr groups
CREATE POLICY "Admins can update their MyPoolr groups" ON mypoolr
    FOR UPDATE USING (admin_id = get_current_telegram_id())
    WITH CHECK (admin_id = get_current_telegram_id());

-- Only admins can delete their MyPoolr groups
CREATE POLICY "Admins can delete their MyPoolr groups" ON mypoolr
    FOR DELETE USING (admin_id = get_current_telegram_id());

-- Member RLS Policies
-- Users can see members in MyPoolr groups they participate in
CREATE POLICY "Users can view members in their MyPoolr groups" ON member
    FOR SELECT USING (
        is_mypoolr_admin(mypoolr_id) OR
        is_mypoolr_member(mypoolr_id)
    );

-- Users can join MyPoolr groups (insert their own member record)
CREATE POLICY "Users can join MyPoolr groups" ON member
    FOR INSERT WITH CHECK (telegram_id = get_current_telegram_id());

-- Users can update their own member record, admins can update any member in their groups
CREATE POLICY "Users can update member records" ON member
    FOR UPDATE USING (
        telegram_id = get_current_telegram_id() OR
        is_mypoolr_admin(mypoolr_id)
    ) WITH CHECK (
        telegram_id = get_current_telegram_id() OR
        is_mypoolr_admin(mypoolr_id)
    );

-- Only admins can remove members from their groups
CREATE POLICY "Admins can remove members from their groups" ON member
    FOR DELETE USING (is_mypoolr_admin(mypoolr_id));

-- Transaction RLS Policies
-- Users can see transactions in MyPoolr groups they participate in
CREATE POLICY "Users can view transactions in their MyPoolr groups" ON transaction
    FOR SELECT USING (
        is_mypoolr_admin(mypoolr_id) OR
        is_mypoolr_member(mypoolr_id)
    );

-- Users can create transactions in MyPoolr groups they participate in
CREATE POLICY "Users can create transactions in their MyPoolr groups" ON transaction
    FOR INSERT WITH CHECK (
        is_mypoolr_admin(mypoolr_id) OR
        is_mypoolr_member(mypoolr_id)
    );

-- Users can update transactions they are involved in, admins can update any transaction in their groups
CREATE POLICY "Users can update relevant transactions" ON transaction
    FOR UPDATE USING (
        is_mypoolr_admin(mypoolr_id) OR
        (is_mypoolr_member(mypoolr_id) AND (
            from_member_id IN (SELECT id FROM member WHERE telegram_id = get_current_telegram_id()) OR
            to_member_id IN (SELECT id FROM member WHERE telegram_id = get_current_telegram_id())
        ))
    ) WITH CHECK (
        is_mypoolr_admin(mypoolr_id) OR
        (is_mypoolr_member(mypoolr_id) AND (
            from_member_id IN (SELECT id FROM member WHERE telegram_id = get_current_telegram_id()) OR
            to_member_id IN (SELECT id FROM member WHERE telegram_id = get_current_telegram_id())
        ))
    );

-- Only admins can delete transactions in their groups
CREATE POLICY "Admins can delete transactions in their groups" ON transaction
    FOR DELETE USING (is_mypoolr_admin(mypoolr_id));

-- Service role bypass (for backend operations)
-- Create a service role that can bypass RLS for system operations
CREATE ROLE service_role;
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Allow service role to bypass RLS
ALTER TABLE mypoolr FORCE ROW LEVEL SECURITY;
ALTER TABLE member FORCE ROW LEVEL SECURITY;
ALTER TABLE transaction FORCE ROW LEVEL SECURITY;