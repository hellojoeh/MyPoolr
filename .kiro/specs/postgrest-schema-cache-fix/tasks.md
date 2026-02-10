# Tasks: PostgREST Schema Cache Fix

## 1. Diagnosis and Verification
- [x] 1.1 Verify actual database schema has `admin_id` column
- [x] 1.2 Confirm PostgREST error references `adminname`
- [x] 1.3 Document the schema mismatch details

## 2. Execute Schema Cache Reload
- [x] 2.1 Access Supabase production dashboard
- [ ] 2.2 Execute schema cache reload command
- [ ] 2.3 Verify cache reload completed successfully

## 3. Production Testing
- [ ] 3.1 Test mypoolr creation via Telegram bot
- [ ] 3.2 Test mypoolr creation via direct API call
- [ ] 3.3 Verify all mypoolr endpoints work correctly
- [ ] 3.4 Check for any remaining schema cache errors

## 4. Documentation
- [x] 4.1 Update DEPLOYMENT_CHECKLIST.md with schema cache reload step
- [x] 4.2 Create troubleshooting guide for schema cache issues
- [ ] 4.3 Document the fix in production deployment guide

## 5. Prevention Measures
- [ ] 5.1 Add schema cache reload to deployment scripts
- [x] 5.2 Add monitoring for PGRST204 errors
- [ ] 5.3 Update migration process documentation

## Task Details

### 1.1 Verify actual database schema
**Description**: Connect to production database and verify the mypoolr table schema
**Commands**:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'mypoolr' 
ORDER BY ordinal_position;
```
**Expected**: Should see `admin_id` column of type `bigint`

### 1.2 Confirm PostgREST error
**Description**: Review the error message from production logs
**Expected**: Error message should reference `adminname` column not found

### 2.1 Access Supabase dashboard
**Description**: Log into Supabase dashboard for production project
**URL**: https://supabase.com/dashboard/project/<project-id>

### 2.2 Execute schema cache reload
**Description**: Reload PostgREST schema cache using one of these methods:

**Method 1 - SQL Command** (Recommended):
```sql
NOTIFY pgrst, 'reload schema';
```

**Method 2 - Supabase Dashboard**:
1. Go to API Settings
2. Click "Reload schema cache" button

**Method 3 - API Call**:
```bash
curl -X POST \
  'https://<project-ref>.supabase.co/rest/v1/rpc/reload_schema_cache' \
  -H 'apikey: <anon-key>' \
  -H 'Authorization: Bearer <service-role-key>'
```

### 3.1 Test via Telegram bot
**Description**: Use the Telegram bot to create a test MyPoolr group
**Steps**:
1. Open Telegram bot
2. Use /createmypoolr command
3. Fill in all required details
4. Verify successful creation

### 3.2 Test via direct API
**Description**: Test the API endpoint directly
**Script**:
```python
import requests
import os

API_URL = os.getenv('BACKEND_URL')
response = requests.post(
    f"{API_URL}/mypoolr/create",
    json={
        "name": "Test Schema Fix",
        "admin_id": 123456789,
        "contribution_amount": 1000.0,
        "rotation_frequency": "monthly",
        "member_limit": 10,
        "tier": "starter"
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### 4.1 Update deployment checklist
**Description**: Add schema cache reload step to deployment checklist
**File**: `DEPLOYMENT_CHECKLIST.md`
**Addition**:
```markdown
### After Database Migrations
- [ ] Run all migration SQL files
- [ ] Verify migrations applied successfully
- [ ] **Reload PostgREST schema cache** (CRITICAL)
  - Method: Run `NOTIFY pgrst, 'reload schema';` in SQL editor
  - Or: Use Supabase Dashboard > API Settings > Reload Schema Cache
- [ ] Test affected API endpoints
- [ ] Monitor for schema-related errors
```

### 4.2 Create troubleshooting guide
**Description**: Create a guide for diagnosing and fixing schema cache issues
**File**: `TROUBLESHOOTING_SCHEMA_CACHE.md`
**Content**: Include symptoms, diagnosis steps, fix procedures, and prevention

### 5.1 Add to deployment scripts
**Description**: Update deployment automation to include cache reload
**File**: `deploy_production.py`
**Addition**: Add function to reload schema cache after migrations

### 5.2 Add monitoring
**Description**: Add error detection for schema cache issues
**File**: `backend/error_handlers.py`
**Addition**: Detect PGRST204 errors and log with actionable information

## Priority

🔴 **CRITICAL**: Tasks 1.1-3.4 (Immediate fix required)
🟡 **HIGH**: Tasks 4.1-4.3 (Documentation)
🟢 **MEDIUM**: Tasks 5.1-5.3 (Prevention)

## Estimated Time

- Diagnosis: 15 minutes
- Fix execution: 15 minutes
- Testing: 30 minutes
- Documentation: 1 hour
- Prevention: 1 hour
- **Total**: ~3 hours
