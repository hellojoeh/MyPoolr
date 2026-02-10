-- Add country column to mypoolr table for currency and payment method support
-- Run this in your Supabase SQL editor

-- Step 1: Add country column with default value
ALTER TABLE mypoolr 
ADD COLUMN country VARCHAR(2) DEFAULT 'KE' 
CHECK (length(country) = 2);

-- Step 2: Create index for efficient country-based queries
CREATE INDEX IF NOT EXISTS idx_mypoolr_country ON mypoolr(country);

-- Step 3: Update any existing records to have the default country
UPDATE mypoolr SET country = 'KE' WHERE country IS NULL;

-- Step 4: Make the country column required (NOT NULL)
ALTER TABLE mypoolr ALTER COLUMN country SET NOT NULL;

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'mypoolr' AND column_name = 'country';