-- MyPoolr Circles Database Schema
-- Initial migration for core tables with relationships and constraints

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types/enums
CREATE TYPE rotation_frequency AS ENUM ('daily', 'weekly', 'monthly');
CREATE TYPE tier_level AS ENUM ('starter', 'essential', 'advanced', 'extended');
CREATE TYPE mypoolr_status AS ENUM ('active', 'paused', 'completed', 'cancelled');
CREATE TYPE member_status AS ENUM ('active', 'pending', 'suspended', 'removed');
CREATE TYPE security_deposit_status AS ENUM ('pending', 'confirmed', 'locked', 'returned', 'used');
CREATE TYPE transaction_type AS ENUM ('contribution', 'security_deposit', 'tier_upgrade', 'deposit_return', 'default_coverage');
CREATE TYPE confirmation_status AS ENUM ('pending', 'sender_confirmed', 'recipient_confirmed', 'both_confirmed', 'cancelled');

-- MyPoolr table (savings groups)
CREATE TABLE mypoolr (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL CHECK (length(name) > 0),
    admin_id BIGINT NOT NULL, -- Telegram user ID
    contribution_amount DECIMAL(15,2) NOT NULL CHECK (contribution_amount > 0),
    rotation_frequency rotation_frequency NOT NULL,
    member_limit INTEGER NOT NULL CHECK (member_limit >= 2 AND member_limit <= 100),
    tier tier_level NOT NULL DEFAULT 'starter',
    security_deposit_multiplier DECIMAL(3,2) NOT NULL DEFAULT 1.0 CHECK (security_deposit_multiplier >= 0.5 AND security_deposit_multiplier <= 3.0),
    status mypoolr_status NOT NULL DEFAULT 'active',
    current_rotation_position INTEGER NOT NULL DEFAULT 0,
    total_rotations_completed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Member table (group participants)
CREATE TABLE member (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mypoolr_id UUID NOT NULL REFERENCES mypoolr(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL CHECK (length(name) > 0),
    phone_number VARCHAR(15) NOT NULL CHECK (length(phone_number) >= 10),
    rotation_position INTEGER NOT NULL CHECK (rotation_position >= 1),
    security_deposit_amount DECIMAL(15,2) NOT NULL CHECK (security_deposit_amount >= 0),
    security_deposit_status security_deposit_status NOT NULL DEFAULT 'pending',
    has_received_payout BOOLEAN NOT NULL DEFAULT FALSE,
    is_locked_in BOOLEAN NOT NULL DEFAULT FALSE,
    status member_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    UNIQUE(mypoolr_id, telegram_id), -- One member per group per telegram user
    UNIQUE(mypoolr_id, rotation_position) -- Unique rotation positions within group
);

-- Transaction table (all financial activities)
CREATE TABLE transaction (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mypoolr_id UUID NOT NULL REFERENCES mypoolr(id) ON DELETE CASCADE,
    from_member_id UUID REFERENCES member(id) ON DELETE SET NULL,
    to_member_id UUID REFERENCES member(id) ON DELETE SET NULL,
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    transaction_type transaction_type NOT NULL,
    confirmation_status confirmation_status NOT NULL DEFAULT 'pending',
    sender_confirmed_at TIMESTAMP WITH TIME ZONE,
    recipient_confirmed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    notes TEXT CHECK (length(notes) <= 500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Performance indexes
CREATE INDEX idx_mypoolr_admin_id ON mypoolr(admin_id);
CREATE INDEX idx_mypoolr_status ON mypoolr(status);
CREATE INDEX idx_mypoolr_tier ON mypoolr(tier);

CREATE INDEX idx_member_mypoolr_id ON member(mypoolr_id);
CREATE INDEX idx_member_telegram_id ON member(telegram_id);
CREATE INDEX idx_member_status ON member(status);
CREATE INDEX idx_member_rotation_position ON member(mypoolr_id, rotation_position);
CREATE INDEX idx_member_security_deposit_status ON member(security_deposit_status);

CREATE INDEX idx_transaction_mypoolr_id ON transaction(mypoolr_id);
CREATE INDEX idx_transaction_from_member ON transaction(from_member_id);
CREATE INDEX idx_transaction_to_member ON transaction(to_member_id);
CREATE INDEX idx_transaction_type ON transaction(transaction_type);
CREATE INDEX idx_transaction_status ON transaction(confirmation_status);
CREATE INDEX idx_transaction_created_at ON transaction(created_at);

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to all tables
CREATE TRIGGER update_mypoolr_updated_at BEFORE UPDATE ON mypoolr FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_member_updated_at BEFORE UPDATE ON member FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_transaction_updated_at BEFORE UPDATE ON transaction FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();