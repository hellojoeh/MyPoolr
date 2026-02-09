-- Migration: Tier System Tables
-- Description: Create tables for tier subscriptions and upgrade requests

-- Create tier_subscriptions table
CREATE TABLE IF NOT EXISTS tier_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id BIGINT NOT NULL,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('starter', 'essential', 'advanced', 'extended')),
    subscription_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    subscription_end TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    payment_reference VARCHAR(255),
    auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create tier_upgrade_requests table
CREATE TABLE IF NOT EXISTS tier_upgrade_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id BIGINT NOT NULL,
    current_tier VARCHAR(20) NOT NULL,
    target_tier VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'KES',
    payment_method VARCHAR(50) NOT NULL,
    phone_number VARCHAR(15),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    payment_reference VARCHAR(255),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tier_subscriptions_admin_id ON tier_subscriptions(admin_id);
CREATE INDEX IF NOT EXISTS idx_tier_subscriptions_active ON tier_subscriptions(admin_id, is_active);
CREATE INDEX IF NOT EXISTS idx_tier_upgrade_requests_admin_id ON tier_upgrade_requests(admin_id);
CREATE INDEX IF NOT EXISTS idx_tier_upgrade_requests_status ON tier_upgrade_requests(status);

-- Create RLS policies
ALTER TABLE tier_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tier_upgrade_requests ENABLE ROW LEVEL SECURITY;

-- RLS policy for tier_subscriptions
CREATE POLICY tier_subscriptions_policy ON tier_subscriptions
    FOR ALL USING (auth.uid()::text = admin_id::text);

-- RLS policy for tier_upgrade_requests  
CREATE POLICY tier_upgrade_requests_policy ON tier_upgrade_requests
    FOR ALL USING (auth.uid()::text = admin_id::text);

-- Insert default starter tier for existing admins
INSERT INTO tier_subscriptions (admin_id, tier, subscription_start, is_active)
SELECT DISTINCT admin_id, 'starter', NOW(), TRUE
FROM mypoolr
WHERE admin_id NOT IN (SELECT admin_id FROM tier_subscriptions WHERE is_active = TRUE)
ON CONFLICT DO NOTHING;