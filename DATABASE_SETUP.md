# MyPoolr Circles - Database Setup Guide

## 📊 Database Schema Overview

Your MyPoolr system has a comprehensive database schema with **11 migration files**:

### Core Schema (001-003)
- `001_initial_schema.sql` - Core tables (mypoolr, member, transaction)
- `002_rls_policies.sql` - Row Level Security for multi-tenancy
- `003_invitation_links.sql` - Invitation system

### Feature Extensions (004-011)
- `004_tier_system.sql` - Subscription tiers
- `005_payment_system.sql` - Payment processing
- `006_tier_change_logs.sql` - Tier upgrade tracking
- `007_notification_system.sql` - Notification management
- `008_operation_locks.sql` - Concurrency control
- `009_feature_toggles.sql` - Feature flag system
- `010_feature_toggle_functions.sql` - Feature toggle logic
- `011_localization_system.sql` - Multi-language support

## 🚀 Production Database Setup

### Option 1: Automatic Setup (Recommended)

Your system includes automatic database initialization:

```python
# backend/init_database.py
async def initialize_database():
    # Runs all migrations automatically
    # Verifies tables exist
    # Performs health checks
```

### Option 2: Manual Supabase Setup

If you prefer manual control:

1. **Access Supabase Dashboard**
2. **Go to SQL Editor**
3. **Run migrations in order** (001 → 011)

## 🔧 Database Configuration Status

### ✅ Already Configured:
- **Supabase URL**: `https://lgfwxvdbkavufbchzvuo.supabase.co`
- **API Keys**: Configured in environment
- **Connection**: Tested and working

### 📋 Core Tables Created:

#### `mypoolr` Table
```sql
- id (UUID, Primary Key)
- name (Group name)
- admin_id (Telegram user ID)
- contribution_amount (Decimal)
- rotation_frequency (daily/weekly/monthly)
- member_limit (2-100)
- tier (starter/essential/advanced/extended)
- security_deposit_multiplier (0.5-3.0)
- status (active/paused/completed/cancelled)
```

#### `member` Table
```sql
- id (UUID, Primary Key)
- mypoolr_id (Foreign Key)
- telegram_id (Telegram user ID)
- name (Member name)
- phone_number (Contact)
- rotation_position (1-N)
- security_deposit_amount (Decimal)
- security_deposit_status (pending/confirmed/locked/returned/used)
- has_received_payout (Boolean)
- is_locked_in (Boolean - prevents early departure)
```

#### `transaction` Table
```sql
- id (UUID, Primary Key)
- mypoolr_id (Foreign Key)
- from_member_id (Sender)
- to_member_id (Recipient)
- amount (Decimal)
- transaction_type (contribution/security_deposit/tier_upgrade/etc.)
- confirmation_status (pending/sender_confirmed/recipient_confirmed/both_confirmed)
- metadata (JSONB for flexible data)
```

## 🛠️ Deployment Database Setup

### For Production Deployment:

#### Method 1: Automatic (Recommended)
Your backend will automatically run migrations on startup:

```python
# In main.py lifespan
await initialize_integration()  # Includes database setup
```

#### Method 2: Manual Pre-deployment
Run database setup before deploying:

```bash
# Local setup (before deployment)
cd backend
python init_database.py
```

#### Method 3: Post-deployment Setup
After deploying, trigger database setup:

```bash
# Call the initialization endpoint
curl -X POST https://your-backend-url/admin/init-database \
     -H "Authorization: Bearer YOUR_API_KEY"
```

## 🔍 Database Verification

### Check if Database is Ready:

```bash
# Test database connection
python -c "
import asyncio
from backend.database import db_manager
print('Testing database...')
result = asyncio.run(db_manager.health_check())
print('Database ready!' if result else 'Database not ready')
"
```

### Verify Tables Exist:

```sql
-- Run in Supabase SQL Editor
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

Expected tables:
- `mypoolr`
- `member` 
- `transaction`
- `notification`
- `feature_toggle`
- `localization`
- Plus any additional tables from migrations

## 🚨 Important Notes

### Row Level Security (RLS)
Your database uses RLS for security:
- Each MyPoolr group is isolated
- Members can only access their group data
- Admins have elevated permissions within their groups

### Security Deposit Logic
The schema enforces the no-loss guarantee:
- `security_deposit_amount` calculated per member
- `is_locked_in` prevents early departure after payout
- `has_received_payout` tracks payout status
- `security_deposit_status` manages deposit lifecycle

### Performance Optimizations
- Comprehensive indexes on frequently queried columns
- JSONB metadata for flexible data storage
- Automatic `updated_at` timestamp triggers

## 🎯 Production Checklist

### Before Deployment:
- [x] Supabase project created
- [x] Connection credentials configured
- [x] Migration files ready
- [ ] Database initialized (automatic or manual)

### After Deployment:
- [ ] Verify all tables exist
- [ ] Test database connectivity
- [ ] Confirm RLS policies active
- [ ] Validate sample data operations

### Monitoring:
- [ ] Set up database monitoring in Supabase
- [ ] Configure backup schedules
- [ ] Monitor connection pool usage
- [ ] Track query performance

## 🚀 Ready for Production!

Your database schema is production-ready with:
- ✅ Comprehensive table structure
- ✅ Security policies (RLS)
- ✅ Performance optimizations
- ✅ Automatic initialization
- ✅ No-loss guarantee enforcement

The database will be automatically set up when you deploy your backend! 🎯