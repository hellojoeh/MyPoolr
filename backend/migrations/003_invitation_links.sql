-- Invitation Links Migration
-- Add invitation link management table

-- Invitation link table for secure group invitations
CREATE TABLE invitation_link (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mypoolr_id UUID NOT NULL REFERENCES mypoolr(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_by BIGINT NOT NULL, -- Telegram user ID of admin
    max_uses INTEGER CHECK (max_uses IS NULL OR max_uses > 0),
    current_uses INTEGER NOT NULL DEFAULT 0 CHECK (current_uses >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CHECK (current_uses <= COALESCE(max_uses, current_uses + 1))
);

-- Indexes for performance
CREATE INDEX idx_invitation_link_token ON invitation_link(token);
CREATE INDEX idx_invitation_link_mypoolr_id ON invitation_link(mypoolr_id);
CREATE INDEX idx_invitation_link_created_by ON invitation_link(created_by);
CREATE INDEX idx_invitation_link_expires_at ON invitation_link(expires_at);
CREATE INDEX idx_invitation_link_active ON invitation_link(is_active);

-- Apply updated_at trigger
CREATE TRIGGER update_invitation_link_updated_at 
    BEFORE UPDATE ON invitation_link 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add some useful views for invitation management
CREATE VIEW active_invitations AS
SELECT 
    il.*,
    m.name as mypoolr_name,
    m.admin_id,
    m.member_limit,
    (SELECT COUNT(*) FROM member WHERE mypoolr_id = il.mypoolr_id AND status = 'active') as current_members
FROM invitation_link il
JOIN mypoolr m ON il.mypoolr_id = m.id
WHERE il.is_active = TRUE 
    AND il.expires_at > NOW()
    AND (il.max_uses IS NULL OR il.current_uses < il.max_uses);

-- View for expired/inactive invitations
CREATE VIEW inactive_invitations AS
SELECT 
    il.*,
    m.name as mypoolr_name,
    CASE 
        WHEN il.is_active = FALSE THEN 'deactivated'
        WHEN il.expires_at <= NOW() THEN 'expired'
        WHEN il.max_uses IS NOT NULL AND il.current_uses >= il.max_uses THEN 'max_uses_reached'
        ELSE 'unknown'
    END as inactive_reason
FROM invitation_link il
JOIN mypoolr m ON il.mypoolr_id = m.id
WHERE il.is_active = FALSE 
    OR il.expires_at <= NOW()
    OR (il.max_uses IS NOT NULL AND il.current_uses >= il.max_uses);