# PostgREST Schema Cache Issue - Diagnosis

**Date**: February 10, 2026  
**Environment**: Production (Supabase)  
**Severity**: Critical - Blocking MyPoolr creation

## Issue Summary

MyPoolr creation fails in production with PostgREST schema cache error.

## Error Details

```json
{
  "success": false,
  "error": "databaseerror",
  "message": "Database error: {
    'message': \"Could not find the 'adminname' column of 'mypoolr' in the schema cache\",
    'code': 'PGRST204',
    'hint': None,
    'details': None
  }"
}
```

## Root Cause

**Schema Mismatch**: PostgREST's cached schema is out of sync with actual database schema.

### Actual Database Schema
```sql
CREATE TABLE mypoolr (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    admin_id BIGINT NOT NULL,  -- ✅ CORRECT COLUMN NAME
    contribution_amount DECIMAL(15,2) NOT NULL,
    rotation_frequency rotation_frequency NOT NULL,
    member_limit INTEGER NOT NULL,
    tier tier_level NOT NULL DEFAULT 'starter',
    ...
);
```

### PostgREST Cached Schema
- Looking for: `adminname` ❌ (incorrect/stale)
- Should be: `admin_id` ✅ (correct)

## Why This Happened

1. Database migrations were run successfully
2. PostgREST schema cache was NOT reloaded after migrations
3. PostgREST continues using stale cached schema
4. API requests fail due to column name mismatch

## Impact

- **Affected Operations**: MyPoolr creation via Telegram bot and API
- **User Impact**: Cannot create new savings groups
- **Scope**: Production environment only (local works fine)

## Solution

Execute PostgREST schema cache reload:

```sql
NOTIFY pgrst, 'reload schema';
```

## Prevention

1. Add schema cache reload to deployment checklist
2. Automate cache reload after migrations
3. Monitor for PGRST204 errors
4. Document schema cache management procedures

## Timeline

- **Issue Detected**: February 10, 2026
- **Root Cause Identified**: Schema cache mismatch
- **Fix Applied**: [Pending execution]
- **Verification**: [Pending]

## Related Files

- Schema Definition: `backend/migrations/001_initial_schema.sql`
- API Endpoint: `backend/api/mypoolr.py`
- Model Definition: `backend/models/mypoolr.py`
