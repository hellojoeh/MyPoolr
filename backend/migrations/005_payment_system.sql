-- Migration: Payment System Tables
-- Description: Create tables for payment processing and tracking

-- Create payments table
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id VARCHAR(255) NOT NULL UNIQUE,
    admin_id BIGINT NOT NULL,
    provider VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'KES',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'expired')),
    reference VARCHAR(255) NOT NULL,
    provider_reference VARCHAR(255),
    phone_number VARCHAR(15) NOT NULL,
    description TEXT,
    expires_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create payment_callbacks table for audit trail
CREATE TABLE IF NOT EXISTS payment_callbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    callback_type VARCHAR(50) NOT NULL, -- 'success', 'timeout', 'error'
    raw_data JSONB NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_result TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_payments_payment_id ON payments(payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_admin_id ON payments(admin_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider);
CREATE INDEX IF NOT EXISTS idx_payment_callbacks_payment_id ON payment_callbacks(payment_id);

-- Create RLS policies
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_callbacks ENABLE ROW LEVEL SECURITY;

-- RLS policy for payments
CREATE POLICY payments_policy ON payments
    FOR ALL USING (auth.uid()::text = admin_id::text);

-- RLS policy for payment_callbacks (admin can view their payment callbacks)
CREATE POLICY payment_callbacks_policy ON payment_callbacks
    FOR SELECT USING (
        payment_id IN (
            SELECT payment_id FROM payments WHERE auth.uid()::text = admin_id::text
        )
    );