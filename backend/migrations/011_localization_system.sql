-- Localization System Migration
-- Adds tables for multi-language support and cultural adaptation

-- Create localization types
CREATE TYPE message_category AS ENUM ('ui', 'notification', 'error', 'validation', 'help');
CREATE TYPE localization_status AS ENUM ('active', 'draft', 'deprecated');

-- Supported locales table
CREATE TABLE supported_locale (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locale_code VARCHAR(10) NOT NULL UNIQUE CHECK (length(locale_code) >= 2),
    language_code VARCHAR(2) NOT NULL CHECK (length(language_code) = 2),
    country_code VARCHAR(2) CHECK (length(country_code) = 2),
    language_name VARCHAR(100) NOT NULL CHECK (length(language_name) > 0),
    native_name VARCHAR(100) NOT NULL CHECK (length(native_name) > 0),
    rtl BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    completion_percentage INTEGER DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Message templates table (source messages)
CREATE TABLE message_template (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(200) NOT NULL UNIQUE CHECK (length(key) > 0),
    category message_category NOT NULL,
    default_text TEXT NOT NULL CHECK (length(default_text) > 0),
    description TEXT CHECK (length(description) <= 500),
    placeholders JSONB DEFAULT '[]', -- Array of placeholder names
    context_info JSONB DEFAULT '{}', -- Additional context for translators
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Localized messages table
CREATE TABLE localized_message (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES message_template(id) ON DELETE CASCADE,
    locale_code VARCHAR(10) NOT NULL REFERENCES supported_locale(locale_code) ON DELETE CASCADE,
    translated_text TEXT NOT NULL CHECK (length(translated_text) > 0),
    status localization_status NOT NULL DEFAULT 'active',
    translator_notes TEXT CHECK (length(translator_notes) <= 1000),
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure unique combination of template and locale
    UNIQUE(template_id, locale_code)
);

-- Cultural settings table
CREATE TABLE cultural_setting (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locale_code VARCHAR(10) NOT NULL REFERENCES supported_locale(locale_code) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL CHECK (length(setting_key) > 0),
    setting_value JSONB NOT NULL,
    description TEXT CHECK (length(description) <= 500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure unique combination of locale and setting
    UNIQUE(locale_code, setting_key)
);

-- Performance indexes
CREATE INDEX idx_supported_locale_code ON supported_locale(locale_code);
CREATE INDEX idx_supported_locale_language ON supported_locale(language_code);
CREATE INDEX idx_supported_locale_active ON supported_locale(is_active);

CREATE INDEX idx_message_template_key ON message_template(key);
CREATE INDEX idx_message_template_category ON message_template(category);
CREATE INDEX idx_message_template_active ON message_template(is_active);

CREATE INDEX idx_localized_message_template ON localized_message(template_id);
CREATE INDEX idx_localized_message_locale ON localized_message(locale_code);
CREATE INDEX idx_localized_message_status ON localized_message(status);

CREATE INDEX idx_cultural_setting_locale ON cultural_setting(locale_code);
CREATE INDEX idx_cultural_setting_key ON cultural_setting(setting_key);

-- Apply updated_at triggers
CREATE TRIGGER update_supported_locale_updated_at BEFORE UPDATE ON supported_locale FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_message_template_updated_at BEFORE UPDATE ON message_template FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_localized_message_updated_at BEFORE UPDATE ON localized_message FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cultural_setting_updated_at BEFORE UPDATE ON cultural_setting FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert supported locales
INSERT INTO supported_locale (locale_code, language_code, country_code, language_name, native_name, rtl, completion_percentage) VALUES
('en_US', 'en', 'US', 'English (United States)', 'English (United States)', FALSE, 100),
('en_KE', 'en', 'KE', 'English (Kenya)', 'English (Kenya)', FALSE, 100),
('sw_KE', 'sw', 'KE', 'Swahili (Kenya)', 'Kiswahili (Kenya)', FALSE, 0),
('sw_TZ', 'sw', 'TZ', 'Swahili (Tanzania)', 'Kiswahili (Tanzania)', FALSE, 0),
('en_UG', 'en', 'UG', 'English (Uganda)', 'English (Uganda)', FALSE, 90),
('en_NG', 'en', 'NG', 'English (Nigeria)', 'English (Nigeria)', FALSE, 85),
('yo_NG', 'yo', 'NG', 'Yoruba (Nigeria)', 'Yorùbá (Nigeria)', FALSE, 0),
('ig_NG', 'ig', 'NG', 'Igbo (Nigeria)', 'Igbo (Nigeria)', FALSE, 0),
('ha_NG', 'ha', 'NG', 'Hausa (Nigeria)', 'Hausa (Nigeria)', FALSE, 0),
('fr_FR', 'fr', 'FR', 'French (France)', 'Français (France)', FALSE, 0),
('ar_SA', 'ar', 'SA', 'Arabic (Saudi Arabia)', 'العربية (السعودية)', TRUE, 0);

-- Insert default message templates
INSERT INTO message_template (key, category, default_text, description, placeholders) VALUES
-- UI Messages
('welcome.title', 'ui', 'Welcome to MyPoolr Circles! 🎉', 'Main welcome message title', '[]'),
('welcome.subtitle', 'ui', 'Join or create savings groups with your friends and family', 'Welcome message subtitle', '[]'),
('menu.create_group', 'ui', '🏦 Create New Group', 'Menu option to create a new group', '[]'),
('menu.join_group', 'ui', '👥 Join Group', 'Menu option to join an existing group', '[]'),
('menu.my_groups', 'ui', '📊 My Groups', 'Menu option to view user groups', '[]'),
('menu.settings', 'ui', '⚙️ Settings', 'Menu option for settings', '[]'),
('menu.help', 'ui', '❓ Help', 'Menu option for help', '[]'),

-- Group Creation
('create.group_name', 'ui', 'What would you like to name your group?', 'Prompt for group name', '[]'),
('create.contribution_amount', 'ui', 'How much will each member contribute per rotation?', 'Prompt for contribution amount', '[]'),
('create.rotation_frequency', 'ui', 'How often will the rotations happen?', 'Prompt for rotation frequency', '[]'),
('create.member_limit', 'ui', 'What is the maximum number of members?', 'Prompt for member limit', '[]'),
('create.success', 'ui', '✅ Group "{group_name}" created successfully!', 'Group creation success message', '["group_name"]'),

-- Member Management
('member.invite_link', 'ui', '🔗 Invitation Link', 'Label for invitation link', '[]'),
('member.join_success', 'ui', '🎉 Welcome to {group_name}!', 'Member join success message', '["group_name"]'),
('member.security_deposit', 'ui', 'Security deposit required: {amount} {currency}', 'Security deposit information', '["amount", "currency"]'),
('member.rotation_position', 'ui', 'Your rotation position: #{position}', 'Member rotation position', '["position"]'),

-- Contributions
('contribution.request', 'ui', '💰 Time to contribute to {recipient_name}!', 'Contribution request message', '["recipient_name"]'),
('contribution.amount_due', 'ui', 'Amount due: {amount} {currency}', 'Contribution amount information', '["amount", "currency"]'),
('contribution.confirm_sent', 'ui', '✅ Confirm you sent {amount} {currency}', 'Sender confirmation button', '["amount", "currency"]'),
('contribution.confirm_received', 'ui', '✅ Confirm you received {amount} {currency}', 'Recipient confirmation button', '["amount", "currency"]'),
('contribution.completed', 'ui', '🎉 Contribution completed!', 'Contribution completion message', '[]'),

-- Notifications
('notification.rotation_start', 'notification', '🔄 Your rotation has started! Time to collect contributions.', 'Rotation start notification', '[]'),
('notification.contribution_reminder', 'notification', '⏰ Reminder: Contribution due for {recipient_name}', 'Contribution reminder', '["recipient_name"]'),
('notification.payment_received', 'notification', '💰 Payment received from {sender_name}', 'Payment received notification', '["sender_name"]'),
('notification.default_warning', 'notification', '⚠️ Contribution deadline approaching!', 'Default warning notification', '[]'),

-- Errors
('error.invalid_amount', 'error', 'Please enter a valid amount', 'Invalid amount error', '[]'),
('error.group_full', 'error', 'This group is already full', 'Group full error', '[]'),
('error.insufficient_tier', 'error', 'This feature requires a tier upgrade', 'Insufficient tier error', '[]'),
('error.payment_failed', 'error', 'Payment failed. Please try again.', 'Payment failure error', '[]'),
('error.network_error', 'error', 'Network error. Please check your connection.', 'Network error message', '[]'),

-- Validation
('validation.required_field', 'validation', 'This field is required', 'Required field validation', '[]'),
('validation.min_amount', 'validation', 'Minimum amount is {min_amount} {currency}', 'Minimum amount validation', '["min_amount", "currency"]'),
('validation.max_members', 'validation', 'Maximum {max_members} members allowed', 'Maximum members validation', '["max_members"]'),
('validation.invalid_phone', 'validation', 'Please enter a valid phone number', 'Invalid phone validation', '[]'),

-- Help
('help.how_it_works', 'help', 'How MyPoolr Circles Works', 'Help section title', '[]'),
('help.security_deposit', 'help', 'Security deposits ensure no member loses money if someone defaults', 'Security deposit explanation', '[]'),
('help.rotation_schedule', 'help', 'Members take turns receiving the pool funds according to the rotation schedule', 'Rotation explanation', '[]'),
('help.contact_support', 'help', 'Contact support for help', 'Contact support message', '[]');

-- Insert cultural settings for different locales
INSERT INTO cultural_setting (locale_code, setting_key, setting_value, description) VALUES
-- Currency formatting
('en_US', 'currency_format', '{"symbol": "$", "position": "before", "decimal_places": 2, "thousands_separator": ",", "decimal_separator": "."}', 'US Dollar formatting'),
('en_KE', 'currency_format', '{"symbol": "KSh", "position": "before", "decimal_places": 2, "thousands_separator": ",", "decimal_separator": "."}', 'Kenyan Shilling formatting'),
('sw_KE', 'currency_format', '{"symbol": "KSh", "position": "before", "decimal_places": 2, "thousands_separator": ",", "decimal_separator": "."}', 'Kenyan Shilling formatting (Swahili)'),
('en_NG', 'currency_format', '{"symbol": "₦", "position": "before", "decimal_places": 2, "thousands_separator": ",", "decimal_separator": "."}', 'Nigerian Naira formatting'),

-- Date formatting
('en_US', 'date_format', '{"short": "MM/dd/yyyy", "long": "MMMM d, yyyy", "time": "h:mm a"}', 'US date formatting'),
('en_KE', 'date_format', '{"short": "dd/MM/yyyy", "long": "d MMMM yyyy", "time": "HH:mm"}', 'Kenyan date formatting'),
('sw_KE', 'date_format', '{"short": "dd/MM/yyyy", "long": "d MMMM yyyy", "time": "HH:mm"}', 'Kenyan date formatting (Swahili)'),
('en_NG', 'date_format', '{"short": "dd/MM/yyyy", "long": "d MMMM yyyy", "time": "HH:mm"}', 'Nigerian date formatting'),

-- Number formatting
('en_US', 'number_format', '{"thousands_separator": ",", "decimal_separator": ".", "grouping": [3]}', 'US number formatting'),
('en_KE', 'number_format', '{"thousands_separator": ",", "decimal_separator": ".", "grouping": [3]}', 'Kenyan number formatting'),
('sw_KE', 'number_format', '{"thousands_separator": ",", "decimal_separator": ".", "grouping": [3]}', 'Kenyan number formatting (Swahili)'),
('en_NG', 'number_format', '{"thousands_separator": ",", "decimal_separator": ".", "grouping": [3]}', 'Nigerian number formatting'),

-- Cultural preferences
('sw_KE', 'cultural_preferences', '{"greeting_style": "formal", "time_preference": "flexible", "communication_style": "indirect"}', 'Swahili cultural preferences'),
('en_NG', 'cultural_preferences', '{"greeting_style": "respectful", "time_preference": "relationship_first", "communication_style": "expressive"}', 'Nigerian cultural preferences'),
('ar_SA', 'cultural_preferences', '{"greeting_style": "formal", "time_preference": "flexible", "communication_style": "indirect", "gender_considerations": true}', 'Arabic cultural preferences');