-- Migration: Operation Locks for Concurrent Operation Safety
-- Description: Create table for distributed locking mechanism

-- Create operation_locks table
CREATE TABLE IF NOT EXISTS operation_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lock_type VARCHAR(50) NOT NULL,
    scope VARCHAR(20) NOT NULL DEFAULT 'mypoolr',
    resource_id VARCHAR(255) NOT NULL,
    holder_id VARCHAR(32) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure only one lock per resource and type
    UNIQUE(lock_type, resource_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_operation_locks_resource ON operation_locks(lock_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_operation_locks_expires ON operation_locks(expires_at);
CREATE INDEX IF NOT EXISTS idx_operation_locks_holder ON operation_locks(holder_id);
CREATE INDEX IF NOT EXISTS idx_operation_locks_scope ON operation_locks(scope, resource_id);

-- Create function to automatically clean up expired locks
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM operation_locks 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    IF deleted_count > 0 THEN
        RAISE NOTICE 'Cleaned up % expired locks', deleted_count;
    END IF;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to force release locks by holder
CREATE OR REPLACE FUNCTION force_release_locks_by_holder(holder_id_param VARCHAR(32))
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM operation_locks 
    WHERE holder_id = holder_id_param;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    IF deleted_count > 0 THEN
        RAISE NOTICE 'Force released % locks for holder %', deleted_count, holder_id_param;
    END IF;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get lock status for a resource
CREATE OR REPLACE FUNCTION get_lock_status(lock_type_param VARCHAR(50), resource_id_param VARCHAR(255))
RETURNS TABLE(
    is_locked BOOLEAN,
    holder_id VARCHAR(32),
    expires_at TIMESTAMPTZ,
    time_remaining INTERVAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE WHEN ol.id IS NOT NULL AND ol.expires_at > NOW() THEN TRUE ELSE FALSE END as is_locked,
        ol.holder_id,
        ol.expires_at,
        CASE WHEN ol.expires_at > NOW() THEN ol.expires_at - NOW() ELSE NULL END as time_remaining
    FROM operation_locks ol
    WHERE ol.lock_type = lock_type_param 
    AND ol.resource_id = resource_id_param
    AND ol.expires_at > NOW()
    LIMIT 1;
    
    -- If no active lock found, return default values
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::VARCHAR(32), NULL::TIMESTAMPTZ, NULL::INTERVAL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Enable Row Level Security
ALTER TABLE operation_locks ENABLE ROW LEVEL SECURITY;

-- RLS Policies for operation_locks (system-level table)
CREATE POLICY "System can manage operation locks" ON operation_locks
    FOR ALL USING (true);

-- Create a scheduled job to clean up expired locks every minute
-- Note: This would typically be handled by a cron job or background task
-- For now, we'll rely on the application-level cleanup

-- Add comments for documentation
COMMENT ON TABLE operation_locks IS 'Distributed locks for concurrent operation safety';
COMMENT ON COLUMN operation_locks.lock_type IS 'Type of operation being locked (e.g., rotation_advance, security_deposit)';
COMMENT ON COLUMN operation_locks.scope IS 'Scope of the lock (global, mypoolr, member, transaction)';
COMMENT ON COLUMN operation_locks.resource_id IS 'ID of the resource being locked';
COMMENT ON COLUMN operation_locks.holder_id IS 'Unique identifier of the process holding the lock';
COMMENT ON COLUMN operation_locks.expires_at IS 'When the lock expires and can be automatically released';
COMMENT ON COLUMN operation_locks.metadata IS 'Additional metadata about the lock operation';

-- Create view for active locks
CREATE OR REPLACE VIEW active_operation_locks AS
SELECT 
    id,
    lock_type,
    scope,
    resource_id,
    holder_id,
    expires_at,
    expires_at - NOW() as time_remaining,
    metadata,
    created_at
FROM operation_locks
WHERE expires_at > NOW()
ORDER BY created_at DESC;

COMMENT ON VIEW active_operation_locks IS 'View showing only currently active (non-expired) operation locks';