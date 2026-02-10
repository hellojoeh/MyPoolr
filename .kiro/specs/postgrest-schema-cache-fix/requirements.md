# Requirements: PostgREST Schema Cache Fix

## Problem Statement

When creating a MyPoolr group via the Telegram bot in production, the operation fails with a PostgREST schema cache error:

```
Database error: {'message': "Could not find the 'adminname' column of 'mypoolr' in the schema cache", 'code': 'PGRST204'}
```

**Root Cause**: PostgREST's schema cache is out of sync with the actual database schema. The database correctly has an `admin_id` column, but PostgREST's cached schema is looking for `adminname`.

## User Stories

### 1. As a system administrator
I want PostgREST to have an up-to-date schema cache so that API requests work correctly against the current database schema.

### 2. As a MyPoolr admin
I want to be able to create new MyPoolr groups through the Telegram bot without encountering database errors.

### 3. As a developer
I want a reliable way to refresh PostgREST's schema cache after database migrations so that schema changes are immediately reflected in the API.

## Acceptance Criteria

### 1.1 Schema Cache Diagnosis
- Identify the exact cause of the schema cache mismatch
- Verify the actual database schema has `admin_id` column
- Confirm PostgREST is using stale cache with `adminname`

### 1.2 Schema Cache Refresh Solution
- Implement a method to force PostgREST schema cache reload
- Test that the cache refresh resolves the column mismatch
- Verify mypoolr creation works after cache refresh

### 1.3 Production Verification
- Successfully create a MyPoolr group via Telegram bot in production
- Confirm no schema cache errors occur
- Validate all mypoolr API endpoints work correctly

### 1.4 Prevention Strategy
- Document the schema cache refresh process
- Add schema cache refresh to deployment checklist
- Consider automated cache refresh after migrations

### 1.5 Monitoring
- Add logging to detect future schema cache mismatches
- Document troubleshooting steps for similar issues

## Technical Context

**Database Schema** (correct):
- Table: `mypoolr`
- Column: `admin_id BIGINT NOT NULL`

**PostgREST Behavior**:
- Caches database schema for performance
- Cache can become stale after schema changes
- Error code `PGRST204` indicates column not found in cache

**Deployment Environment**:
- Production: Render.com
- Database: Supabase PostgreSQL
- API Layer: PostgREST (via Supabase)

## Success Metrics

1. MyPoolr creation success rate: 100% in production
2. Zero schema cache errors after fix
3. Schema cache refresh process documented
4. Prevention measures in place

## Out of Scope

- Changing the database schema
- Modifying the API code (already correct)
- Implementing automatic schema migration detection
