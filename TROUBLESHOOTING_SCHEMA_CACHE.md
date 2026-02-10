# Troubleshooting: PostgREST Schema Cache Issues

## Overview

This guide helps diagnose and fix PostgREST schema cache synchronization issues in Supabase deployments.

## Symptoms

### Common Error Messages

**PGRST204 - Column Not Found**
```
Could not find the 'column_name' column of 'table_name' in the schema cache
```

**PGRST202 - Relation Not Found**
```
Could not find the 'table_name' relation in the schema cache
```

### User-Facing Symptoms
- API requests fail with database errors
- Operations work locally but fail in production
- Errors reference non-existent columns or tables
- Database queries work in SQL editor but fail via API

## Root Cause

PostgREST caches the database schema for performance. When schema changes occur (migrations, column additions/renames, table modifications), the cache becomes stale and doesn't reflect the actual database structure.

## Diagnosis Steps

### Step 1: Verify Actual Schema

Connect to your database and check the actual schema:

```sql
-- Check table columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'your_table_name'
ORDER BY ordinal_position;

-- Check table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'your_table_name';
```

### Step 2: Check Error Message

Look for these indicators in error messages:
- Error code: `PGRST204` or `PGRST202`
- Message contains: "schema cache"
- Column/table name mismatch with actual schema

### Step 3: Compare Schema vs Cache

If the actual schema is correct but API fails, the cache is stale.

## Solution Methods

### Method 1: Supabase Dashboard (Easiest)

1. Log into [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Navigate to: **Settings** → **API**
4. Click: **"Reload schema cache"** button
5. Wait for confirmation (usually instant)

**Pros**: Simple, no SQL required  
**Cons**: Requires dashboard access

### Method 2: SQL NOTIFY Command (Recommended)

Execute in SQL Editor:

```sql
NOTIFY pgrst, 'reload schema';
```

**Pros**: Fast, can be automated  
**Cons**: Requires SQL access

### Method 3: API Endpoint (Advanced)

```bash
curl -X POST 'https://YOUR_PROJECT.supabase.co/rest/v1/rpc/reload_schema_cache' \
  -H 'apikey: YOUR_ANON_KEY' \
  -H 'Authorization: Bearer YOUR_SERVICE_KEY'
```

**Pros**: Can be scripted  
**Cons**: Requires API keys

### Method 4: Wait for Auto-Refresh

PostgREST automatically refreshes cache periodically (default: every few minutes).

**Pros**: No action needed  
**Cons**: Slow, unpredictable timing

## Verification

After reloading the cache, verify the fix:

### 1. Test API Endpoint

```bash
# Test the affected endpoint
curl -X POST 'https://YOUR_PROJECT.supabase.co/rest/v1/your_table' \
  -H 'apikey: YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"your_data": "here"}'
```

### 2. Check Application

Test the operation that was failing through your application.

### 3. Monitor Logs

Check for any remaining schema cache errors in logs.

## Prevention

### 1. Add to Deployment Checklist

Always reload schema cache after migrations:

```markdown
## Deployment Steps
1. Run database migrations
2. **Reload PostgREST schema cache** ⚠️
3. Test affected endpoints
4. Deploy application code
```

### 2. Automate Cache Reload

Add to deployment scripts:

```python
# deploy_production.py
def reload_schema_cache():
    """Reload PostgREST schema cache after migrations."""
    import subprocess
    
    print("Reloading PostgREST schema cache...")
    
    # Method 1: SQL command
    subprocess.run([
        'psql', DATABASE_URL,
        '-c', "NOTIFY pgrst, 'reload schema';"
    ])
    
    print("✅ Schema cache reloaded")
```

### 3. Monitor for Cache Errors

Add error detection:

```python
# backend/error_handlers.py
def is_schema_cache_error(error_message: str) -> bool:
    """Detect PostgREST schema cache errors."""
    cache_indicators = [
        'PGRST204',
        'PGRST202',
        'schema cache',
        'could not find'
    ]
    return any(indicator in error_message.lower() for indicator in cache_indicators)

def handle_database_error(error):
    """Handle database errors with schema cache detection."""
    if is_schema_cache_error(str(error)):
        logger.error(
            "PostgREST schema cache mismatch detected!",
            extra={
                "error": str(error),
                "action_required": "Reload schema cache",
                "command": "NOTIFY pgrst, 'reload schema';"
            }
        )
        # Alert ops team
        send_alert("Schema cache reload required")
```

### 4. Document Schema Changes

Keep a migration log:

```markdown
## Migration: 012_add_country_column.sql
- Added: `country` column to `mypoolr` table
- Type: VARCHAR(2)
- **Action Required**: Reload schema cache after applying
```

## Common Scenarios

### Scenario 1: Column Renamed

**Problem**: Renamed `admin_name` to `admin_id` in migration  
**Symptom**: API looks for old `admin_name` column  
**Solution**: Reload schema cache

### Scenario 2: New Table Added

**Problem**: Created new table in migration  
**Symptom**: API returns "relation not found"  
**Solution**: Reload schema cache

### Scenario 3: Column Type Changed

**Problem**: Changed column from VARCHAR to TEXT  
**Symptom**: Type validation errors  
**Solution**: Reload schema cache

### Scenario 4: Column Added

**Problem**: Added new column to existing table  
**Symptom**: Column not accessible via API  
**Solution**: Reload schema cache

## Troubleshooting Checklist

- [ ] Verify actual database schema is correct
- [ ] Confirm error is schema cache related (PGRST204/202)
- [ ] Reload schema cache using one of the methods
- [ ] Wait 1-2 minutes for cache to propagate
- [ ] Test the affected operation
- [ ] Check logs for remaining errors
- [ ] Update deployment documentation
- [ ] Add cache reload to deployment scripts

## When to Contact Support

Contact Supabase support if:
- Schema cache reload doesn't fix the issue
- Cache errors persist after multiple reload attempts
- Auto-refresh is not working
- Experiencing frequent cache synchronization issues

## Related Resources

- [Supabase PostgREST Documentation](https://supabase.com/docs/guides/api)
- [PostgREST Schema Cache](https://postgrest.org/en/stable/schema_cache.html)
- Project deployment checklist: `DEPLOYMENT_CHECKLIST.md`
- Schema cache reload script: `reload_schema_cache.py`
- Test script: `test_mypoolr_creation.py`

## Quick Reference

### Reload Commands

```sql
-- SQL Editor
NOTIFY pgrst, 'reload schema';
```

```bash
# API Call
curl -X POST 'https://PROJECT.supabase.co/rest/v1/rpc/reload_schema_cache' \
  -H 'apikey: KEY' -H 'Authorization: Bearer KEY'
```

```python
# Python Script
python reload_schema_cache.py
```

### Test Commands

```python
# Test MyPoolr creation
python test_mypoolr_creation.py
```

```bash
# Test via curl
curl -X POST 'https://API_URL/mypoolr/create' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test","admin_id":123,...}'
```

## Version History

- **v1.0** (2026-02-10): Initial guide created for `adminname` column issue
