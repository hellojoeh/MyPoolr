-- Migration: Tier Change Logs
-- Description: Create table for tracking tier changes and feature unlocks

-- Create tier_change_logs table
CREATE TABLE IF NOT EXISTS tier_change_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id BIGINT NOT NULL,
    from_tier VARCHAR(20) NOT NULL,
    to_tier VARCHAR(20) NOT NULL,
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('upgrade', 'downgrade', 'expiry')),
    payment_reference VARCHAR(255),
    unlocked_features JSONB DEFAULT '[]',
    disabled_features JSONB DEFAULT '[]',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tier_change_logs_admin_id ON tier_change_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_tier_change_logs_timestamp ON tier_change_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_tier_change_logs_change_type ON tier_change_logs(change_type);

-- Create RLS policy
ALTER TABLE tier_change_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tier_change_logs_policy ON tier_change_logs
    FOR ALL USING (auth.uid()::text = admin_id::text);