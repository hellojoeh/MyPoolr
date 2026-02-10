-- Add country column to mypoolr table for localization support
-- Migration 012: Add country support

-- Add country column to mypoolr table
ALTER TABLE mypoolr 
ADD COLUMN country VARCHAR(2) DEFAULT 'KE' CHECK (length(country) = 2);

-- Create index for country-based queries
CREATE INDEX idx_mypoolr_country ON mypoolr(country);

-- Update existing records to have default country
UPDATE mypoolr SET country = 'KE' WHERE country IS NULL;

-- Make country NOT NULL after setting defaults
ALTER TABLE mypoolr ALTER COLUMN country SET NOT NULL;