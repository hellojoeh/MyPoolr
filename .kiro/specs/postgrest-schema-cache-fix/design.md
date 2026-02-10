# Design: PostgREST Schema Cache Fix

## Overview

This design addresses the PostgREST schema cache synchronization issue causing MyPoolr creation failures in production. The solution involves diagnosing the cache state, implementing a refresh mechanism, and establishing prevention measures.

## Root Cause Analysis

**Problem**: PostgREST error `PGRST204` - "Could not find the 'adminname' column"

**Actual Schema**: `admin_id` column exists in database
**Cached Schema**: PostgREST cache references non-existent `adminname` column

**Why This Happens**:
1. PostgREST caches the database schema for performance
2. Schema changes (migrations) don't automatically invalidate the cache
3. Supabase's PostgREST instance needs explicit cache reload

## Solution Design

### 1. Immediate Fix: Force Schema Cache Reload

**Method 1: NOTIFY Command** (Recommended)
```sql
NOTIFY pgrst, 'reload schema';
```

**Method 2: Supabase Dashboard**
- Navigate to API settings
- Click "Reload schema cache" button

**Method 3: API Endpoint**
```bash
POST https://<project-ref>.supabase.co/rest/v1/rpc/reload_schema_cache
```

### 2. Verification Steps

**Step 1**: Check current schema
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'mypoolr' 
AND column_name LIKE '%admin%';
```

**Step 2**: Reload cache using chosen method

**Step 3**: Test mypoolr creation via API
```python
# Test script
import requests

response = requests.post(
    f"{API_URL}/mypoolr/create",
    json={
        "name": "Test Group",
        "admin_id": 123456789,
        "contribution_amount": 1000,
        "rotation_frequency": "monthly",
        "member_limit": 10,
        "tier": "starter"
    }
)
print(response.json())
```

### 3. Prevention Strategy

**Deployment Checklist Addition**:
```markdown
## After Database Migrations
1. Run all migration files
2. Verify schema changes in database
3. **Reload PostgREST schema cache**
4. Test affected API endpoints
5. Monitor for schema-related errors
```

**Automated Solution** (Future Enhancement):
- Add post-migration hook to reload schema cache
- Include in CI/CD pipeline

### 4. Monitoring & Logging

**Error Detection**:
- Monitor for `PGRST204` errors in logs
- Alert on schema cache mismatches
- Track API error rates

**Logging Enhancement**:
```python
# Add to error handlers
if 'PGRST204' in error_message:
    logger.error(
        "PostgREST schema cache mismatch detected",
        extra={
            "error_code": "PGRST204",
            "table": extract_table_name(error_message),
            "column": extract_column_name(error_message),
            "action": "Schema cache reload required"
        }
    )
```

## Implementation Plan

### Phase 1: Immediate Fix (Critical)
1. Access Supabase dashboard for production project
2. Execute schema cache reload
3. Test mypoolr creation via Telegram bot
4. Verify fix resolves the issue

### Phase 2: Documentation
1. Document the fix in deployment guide
2. Add schema cache reload to deployment checklist
3. Create troubleshooting guide for similar issues

### Phase 3: Prevention
1. Update deployment scripts to include cache reload
2. Add monitoring for schema cache errors
3. Consider automated cache refresh after migrations

## Testing Strategy

### Manual Testing
1. **Pre-fix**: Attempt mypoolr creation (should fail)
2. **Execute fix**: Reload schema cache
3. **Post-fix**: Attempt mypoolr creation (should succeed)
4. **Verification**: Create multiple mypoolrs with different parameters

### Regression Testing
- Test all mypoolr API endpoints
- Verify member creation still works
- Check invitation link generation
- Validate tier management

## Rollback Plan

**If cache reload causes issues**:
1. Schema cache will auto-refresh from database
2. No permanent changes made to database
3. Can re-run migrations if needed

**Risk**: Very low - cache reload is a safe operation

## Success Criteria

✅ MyPoolr creation works in production
✅ No PGRST204 errors in logs
✅ All API endpoints function correctly
✅ Documentation updated
✅ Prevention measures in place

## Dependencies

- Access to Supabase dashboard (production)
- Database connection for SQL commands
- API testing capability

## Timeline

- **Immediate**: 15 minutes (execute cache reload)
- **Documentation**: 30 minutes
- **Prevention setup**: 1 hour
- **Total**: ~2 hours

## Correctness Properties

### Property 1: Schema Consistency
**Statement**: PostgREST's cached schema must match the actual database schema
**Validates**: Requirements 1.1, 1.2

**Test Strategy**:
```python
def test_schema_consistency():
    # Get actual schema from database
    actual_columns = get_db_columns('mypoolr')
    
    # Get schema from PostgREST API
    api_response = requests.get(f"{API_URL}/mypoolr?limit=0")
    cached_columns = extract_columns_from_headers(api_response.headers)
    
    # Verify they match
    assert actual_columns == cached_columns
```

### Property 2: API Request Success
**Statement**: All valid mypoolr creation requests must succeed after cache reload
**Validates**: Requirements 1.2, 1.3

**Test Strategy**:
```python
def test_mypoolr_creation_success():
    valid_requests = generate_valid_mypoolr_requests(n=10)
    
    for request in valid_requests:
        response = create_mypoolr(request)
        assert response.status_code == 200
        assert 'id' in response.json()
```

### Property 3: Error Recovery
**Statement**: Schema cache errors must be detectable and recoverable
**Validates**: Requirements 1.4, 1.5

**Test Strategy**:
```python
def test_cache_error_detection():
    # Simulate cache mismatch
    error = simulate_pgrst204_error()
    
    # Verify error is detected
    assert is_schema_cache_error(error)
    
    # Verify recovery procedure exists
    assert has_recovery_procedure('PGRST204')
```

## Notes

- This is a production-critical fix
- No code changes required (infrastructure issue)
- Low risk, high impact solution
- Should be executed immediately
