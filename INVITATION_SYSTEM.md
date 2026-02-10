# World-Class Invitation Link System for MyPoolr

## Overview
A comprehensive invitation system that generates secure, trackable, and user-friendly invitation links for MyPoolr groups.

## Current Implementation

### 1. Invitation Code Format
```
MYPOOLR-{GROUP_ID}-{RANDOM_CODE}
Example: MYPOOLR-42680-20176
```

### 2. Invitation Link Types

#### A. Deep Link (Telegram Native)
```
https://t.me/{bot_username}?start={invitation_code}
```
**Benefits:**
- Opens directly in Telegram app
- Seamless user experience
- No external browser needed
- Automatic bot start with context

**Implementation:**
```python
bot_username = (await context.bot.get_me()).username
invite_link = f"https://t.me/{bot_username}?start={invitation_code}"
```

#### B. Web Link (Universal)
```
https://mypoolr.app/join/{invitation_code}
```
**Benefits:**
- Works from any browser
- Can show preview/landing page
- Better for sharing on non-Telegram platforms
- SEO friendly

**Implementation:**
- Requires a web frontend
- Redirects to Telegram deep link
- Shows group preview before joining

## World-Class Features to Implement

### 1. **Secure Code Generation**
```python
import secrets
import hashlib
from datetime import datetime

def generate_invitation_code(mypoolr_id: str) -> str:
    """Generate cryptographically secure invitation code."""
    # Use secrets for cryptographic randomness
    random_part = secrets.token_hex(3).upper()  # 6 characters
    
    # Add timestamp-based component for uniqueness
    timestamp = int(datetime.utcnow().timestamp())
    time_hash = hashlib.sha256(str(timestamp).encode()).hexdigest()[:5].upper()
    
    return f"MYPOOLR-{mypoolr_id}-{random_part}{time_hash}"
```

### 2. **Link Expiration**
```python
from datetime import datetime, timedelta

class InvitationLink:
    def __init__(self, code: str, expires_in_days: int = 30):
        self.code = code
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(days=expires_in_days)
        self.is_active = True
        self.max_uses = None  # Unlimited by default
        self.use_count = 0
    
    def is_valid(self) -> bool:
        """Check if invitation is still valid."""
        if not self.is_active:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses and self.use_count >= self.max_uses:
            return False
        return True
```

### 3. **Link Analytics & Tracking**
```python
class InvitationAnalytics:
    """Track invitation link performance."""
    
    def __init__(self, invitation_code: str):
        self.code = invitation_code
        self.views = 0
        self.clicks = 0
        self.joins = 0
        self.conversion_rate = 0.0
        self.referrer_sources = {}  # Track where links are shared
        self.view_timestamps = []
        self.join_timestamps = []
    
    def record_view(self, source: str = "unknown"):
        """Record when someone views the invitation."""
        self.views += 1
        self.view_timestamps.append(datetime.utcnow())
        self.referrer_sources[source] = self.referrer_sources.get(source, 0) + 1
    
    def record_join(self):
        """Record successful join."""
        self.joins += 1
        self.join_timestamps.append(datetime.utcnow())
        self.conversion_rate = (self.joins / self.views * 100) if self.views > 0 else 0
```

### 4. **QR Code Generation**
```python
import qrcode
from io import BytesIO

def generate_qr_code(invitation_link: str) -> BytesIO:
    """Generate QR code for invitation link."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(invitation_link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO for sending via Telegram
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio
```

### 5. **Smart Link Sharing**
```python
async def share_invitation_smart(update: Update, context: ContextTypes.DEFAULT_TYPE, invitation_code: str):
    """Smart invitation sharing with multiple options."""
    bot_username = (await context.bot.get_me()).username
    deep_link = f"https://t.me/{bot_username}?start={invitation_code}"
    
    # Generate shareable message
    share_message = f"""
🎯 *Join My MyPoolr Group!*

I'm inviting you to join our savings circle on MyPoolr.

*Quick Join:*
{deep_link}

*Or use code:* `{invitation_code}`

Tap the link above or use /join {invitation_code}
    """.strip()
    
    # Create sharing options
    grid = button_manager.create_grid()
    
    # Telegram share button (uses Telegram's native sharing)
    share_url = f"https://t.me/share/url?url={deep_link}&text=Join my MyPoolr savings group!"
    grid.add_row([
        button_manager.create_button("📤 Share on Telegram", share_url, url=True)
    ])
    
    # WhatsApp share
    whatsapp_text = f"Join my MyPoolr savings group: {deep_link}"
    whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(whatsapp_text)}"
    grid.add_row([
        button_manager.create_button("💬 Share on WhatsApp", whatsapp_url, url=True)
    ])
    
    # Copy to clipboard (via inline query)
    grid.add_row([
        button_manager.create_button("📋 Copy Link", f"copy_link:{invitation_code}"),
        button_manager.create_button("📱 Generate QR", f"generate_qr:{invitation_code}")
    ])
    
    return share_message, grid
```

### 6. **Link Validation & Security**
```python
class InvitationValidator:
    """Validate invitation codes and prevent abuse."""
    
    @staticmethod
    def validate_code_format(code: str) -> bool:
        """Validate invitation code format."""
        import re
        pattern = r'^MYPOOLR-\d+-[A-Z0-9]+$'
        return bool(re.match(pattern, code))
    
    @staticmethod
    async def check_rate_limit(user_id: int, redis_client) -> bool:
        """Prevent spam by rate limiting join attempts."""
        key = f"join_attempts:{user_id}"
        attempts = await redis_client.get(key)
        
        if attempts and int(attempts) >= 5:  # Max 5 attempts per hour
            return False
        
        await redis_client.incr(key)
        await redis_client.expire(key, 3600)  # 1 hour
        return True
    
    @staticmethod
    async def check_duplicate_join(user_id: int, mypoolr_id: str, db) -> bool:
        """Check if user already joined this group."""
        query = """
            SELECT COUNT(*) FROM members 
            WHERE telegram_id = $1 AND mypoolr_id = $2
        """
        count = await db.fetchval(query, user_id, mypoolr_id)
        return count == 0
```

### 7. **Database Schema**
```sql
-- Invitation links table
CREATE TABLE invitation_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mypoolr_id UUID NOT NULL REFERENCES mypoolrs(id) ON DELETE CASCADE,
    invitation_code VARCHAR(50) UNIQUE NOT NULL,
    created_by UUID NOT NULL REFERENCES members(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    max_uses INTEGER,
    use_count INTEGER DEFAULT 0,
    
    -- Analytics
    view_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    join_count INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    INDEX idx_invitation_code (invitation_code),
    INDEX idx_mypoolr_id (mypoolr_id),
    INDEX idx_expires_at (expires_at)
);

-- Invitation analytics table
CREATE TABLE invitation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invitation_link_id UUID NOT NULL REFERENCES invitation_links(id) ON DELETE CASCADE,
    event_type VARCHAR(20) NOT NULL, -- 'view', 'click', 'join'
    user_id BIGINT, -- Telegram user ID (nullable for views)
    source VARCHAR(50), -- 'telegram', 'whatsapp', 'direct', etc.
    referrer VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_invitation_link_id (invitation_link_id),
    INDEX idx_event_type (event_type),
    INDEX idx_created_at (created_at)
);
```

### 8. **Backend API Endpoints**
```python
# In backend/api/invitation.py

@router.post("/invitations/create")
async def create_invitation_link(
    mypoolr_id: UUID,
    expires_in_days: int = 30,
    max_uses: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new invitation link."""
    # Generate secure code
    invitation_code = generate_invitation_code(str(mypoolr_id))
    
    # Store in database
    query = """
        INSERT INTO invitation_links 
        (mypoolr_id, invitation_code, created_by, expires_at, max_uses)
        VALUES ($1, $2, $3, NOW() + INTERVAL '$4 days', $5)
        RETURNING *
    """
    link = await db.fetchrow(
        query, mypoolr_id, invitation_code, 
        current_user['id'], expires_in_days, max_uses
    )
    
    return {
        "success": True,
        "invitation_code": invitation_code,
        "expires_at": link['expires_at'],
        "deep_link": f"https://t.me/{BOT_USERNAME}?start={invitation_code}"
    }

@router.post("/invitations/{code}/validate")
async def validate_invitation(code: str, user_id: int):
    """Validate invitation code and record analytics."""
    # Check format
    if not InvitationValidator.validate_code_format(code):
        raise HTTPException(400, "Invalid invitation code format")
    
    # Fetch invitation
    query = """
        SELECT * FROM invitation_links 
        WHERE invitation_code = $1 AND is_active = TRUE
    """
    invitation = await db.fetchrow(query, code)
    
    if not invitation:
        raise HTTPException(404, "Invitation not found or inactive")
    
    # Check expiration
    if invitation['expires_at'] and invitation['expires_at'] < datetime.utcnow():
        raise HTTPException(410, "Invitation has expired")
    
    # Check max uses
    if invitation['max_uses'] and invitation['use_count'] >= invitation['max_uses']:
        raise HTTPException(410, "Invitation has reached maximum uses")
    
    # Check duplicate join
    if not await InvitationValidator.check_duplicate_join(user_id, invitation['mypoolr_id'], db):
        raise HTTPException(409, "You have already joined this group")
    
    # Record analytics
    await record_invitation_event(invitation['id'], 'view', user_id)
    
    return {
        "success": True,
        "valid": True,
        "mypoolr_id": invitation['mypoolr_id']
    }

@router.get("/invitations/{code}/analytics")
async def get_invitation_analytics(
    code: str,
    current_user: dict = Depends(get_current_user)
):
    """Get analytics for an invitation link."""
    query = """
        SELECT 
            il.*,
            COUNT(CASE WHEN ia.event_type = 'view' THEN 1 END) as views,
            COUNT(CASE WHEN ia.event_type = 'click' THEN 1 END) as clicks,
            COUNT(CASE WHEN ia.event_type = 'join' THEN 1 END) as joins,
            CASE 
                WHEN COUNT(CASE WHEN ia.event_type = 'view' THEN 1 END) > 0 
                THEN (COUNT(CASE WHEN ia.event_type = 'join' THEN 1 END)::float / 
                      COUNT(CASE WHEN ia.event_type = 'view' THEN 1 END) * 100)
                ELSE 0 
            END as conversion_rate
        FROM invitation_links il
        LEFT JOIN invitation_analytics ia ON il.id = ia.invitation_link_id
        WHERE il.invitation_code = $1
        GROUP BY il.id
    """
    analytics = await db.fetchrow(query, code)
    
    if not analytics:
        raise HTTPException(404, "Invitation not found")
    
    return {
        "success": True,
        "analytics": dict(analytics)
    }
```

## Implementation Priority

### Phase 1: Core Functionality (Immediate)
1. ✅ Basic invitation code generation
2. ✅ Telegram deep links
3. ✅ Share link handler
4. 🔄 Backend API for invitation creation
5. 🔄 Database schema implementation

### Phase 2: Security & Validation (Week 1)
1. Secure code generation with secrets
2. Link expiration
3. Rate limiting
4. Duplicate join prevention
5. Code format validation

### Phase 3: Analytics & Tracking (Week 2)
1. View/click/join tracking
2. Analytics dashboard
3. Conversion rate calculation
4. Source tracking

### Phase 4: Enhanced Features (Week 3)
1. QR code generation
2. WhatsApp/Email sharing
3. Custom expiration dates
4. Max uses limit
5. Link deactivation

### Phase 5: Advanced Features (Week 4)
1. Web landing page
2. Link preview with group info
3. A/B testing for invitation messages
4. Referral rewards
5. Admin analytics dashboard

## Best Practices

1. **Security First**
   - Use cryptographically secure random generation
   - Validate all inputs
   - Rate limit join attempts
   - Prevent duplicate joins

2. **User Experience**
   - Make links easy to share
   - Provide multiple sharing options
   - Show clear error messages
   - Track analytics for optimization

3. **Performance**
   - Cache invitation data in Redis
   - Use database indexes
   - Batch analytics writes
   - Optimize query performance

4. **Monitoring**
   - Track invitation success rates
   - Monitor for abuse patterns
   - Alert on unusual activity
   - Log all invitation events

## Testing Checklist

- [ ] Generate invitation code
- [ ] Create deep link
- [ ] Share via Telegram
- [ ] Share via WhatsApp
- [ ] Generate QR code
- [ ] Validate code format
- [ ] Check expiration
- [ ] Prevent duplicate joins
- [ ] Rate limit enforcement
- [ ] Analytics tracking
- [ ] Admin dashboard
- [ ] Error handling
