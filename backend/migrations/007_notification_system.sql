-- Migration: Notification System
-- Description: Create tables for comprehensive notification system with localization support

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mypoolr_id UUID REFERENCES mypoolr(id) ON DELETE CASCADE,
    recipient_id BIGINT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    channel VARCHAR(20) DEFAULT 'telegram',
    
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    metadata JSONB DEFAULT '{}',
    template_data JSONB DEFAULT '{}',
    
    language_code VARCHAR(5) DEFAULT 'en',
    country_code VARCHAR(2) DEFAULT 'US',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create notification templates table
CREATE TABLE IF NOT EXISTS notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_key VARCHAR(100) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    language_code VARCHAR(5) NOT NULL,
    country_code VARCHAR(2) NOT NULL,
    
    title_template VARCHAR(200) NOT NULL,
    message_template TEXT NOT NULL,
    
    variables JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(notification_type, language_code, country_code)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_notifications_recipient_status ON notifications(recipient_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_mypoolr_type ON notifications(mypoolr_id, notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_status ON notifications(scheduled_at, status);
CREATE INDEX IF NOT EXISTS idx_notifications_type_priority ON notifications(notification_type, priority);
CREATE INDEX IF NOT EXISTS idx_notification_templates_lookup ON notification_templates(notification_type, language_code, country_code);

-- Create updated_at trigger for notifications
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_notifications_updated_at 
    BEFORE UPDATE ON notifications 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_templates_updated_at 
    BEFORE UPDATE ON notification_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default notification templates
INSERT INTO notification_templates (template_key, notification_type, language_code, country_code, title_template, message_template, variables) VALUES
('rotation_start_en_us', 'rotation_start', 'en', 'US', '🎯 Your Turn in {mypoolr_name}', 'It''s your turn to receive contributions in {mypoolr_name}! Expected amount: {expected_amount}. {contributor_count} members will contribute.', '{"mypoolr_name": "Group name", "expected_amount": "Expected contribution amount", "contributor_count": "Number of contributors"}'),

('contribution_reminder_en_us', 'contribution_reminder', 'en', 'US', '💰 Contribution Due in {mypoolr_name}', 'Please contribute {amount} to {recipient_name} in {mypoolr_name}. Deadline: {deadline}', '{"mypoolr_name": "Group name", "amount": "Contribution amount", "recipient_name": "Recipient name", "deadline": "Contribution deadline"}'),

('contribution_confirmed_en_us', 'contribution_confirmed', 'en', 'US', '✅ Contribution Confirmed', 'Contribution of {amount} from {sender_name} has been confirmed in {mypoolr_name}.', '{"amount": "Contribution amount", "sender_name": "Sender name", "mypoolr_name": "Group name"}'),

('rotation_complete_en_us', 'rotation_complete', 'en', 'US', '🎉 Rotation Complete in {mypoolr_name}', 'All contributions for {recipient_name} have been confirmed in {mypoolr_name}. Total received: {total_amount}', '{"mypoolr_name": "Group name", "recipient_name": "Recipient name", "total_amount": "Total amount received"}'),

('default_warning_en_us', 'default_warning', 'en', 'US', '⚠️ Contribution Deadline Approaching', 'Your contribution of {amount} to {recipient_name} in {mypoolr_name} is due in {hours_remaining} hours!', '{"amount": "Contribution amount", "recipient_name": "Recipient name", "mypoolr_name": "Group name", "hours_remaining": "Hours until deadline"}'),

('default_handled_en_us', 'default_handled', 'en', 'US', '🚨 Default Handled', 'A missed contribution in {mypoolr_name} has been covered using security deposit. Member: {member_name}, Amount: {amount}', '{"mypoolr_name": "Group name", "member_name": "Defaulted member name", "amount": "Default amount"}'),

('security_deposit_required_en_us', 'security_deposit_required', 'en', 'US', '🔒 Security Deposit Required', 'Please provide security deposit of {amount} to join {mypoolr_name}. This ensures protection for all members.', '{"amount": "Security deposit amount", "mypoolr_name": "Group name"}'),

('security_deposit_returned_en_us', 'security_deposit_returned', 'en', 'US', '💰 Security Deposit Returned', 'Your security deposit of {amount} has been returned from {mypoolr_name}. Thank you for completing the cycle!', '{"amount": "Security deposit amount", "mypoolr_name": "Group name"}'),

('member_joined_en_us', 'member_joined', 'en', 'US', '👋 New Member Joined', '{member_name} has joined {mypoolr_name}. Total members: {total_members}', '{"member_name": "New member name", "mypoolr_name": "Group name", "total_members": "Total member count"}'),

('member_left_en_us', 'member_left', 'en', 'US', '👋 Member Left', '{member_name} has left {mypoolr_name}. Total members: {total_members}', '{"member_name": "Member name", "mypoolr_name": "Group name", "total_members": "Total member count"}'),

('tier_upgraded_en_us', 'tier_upgraded', 'en', 'US', '⬆️ Tier Upgraded', 'Your MyPoolr tier has been upgraded to {new_tier}! New features are now available.', '{"new_tier": "New tier name"}'),

('tier_downgraded_en_us', 'tier_downgraded', 'en', 'US', '⬇️ Tier Downgraded', 'Your MyPoolr tier has been downgraded to {new_tier} due to subscription expiry. Your data is preserved.', '{"new_tier": "New tier name"}'),

('system_alert_en_us', 'system_alert', 'en', 'US', '🔔 System Alert', '{alert_message}', '{"alert_message": "Alert message content"}')

ON CONFLICT (notification_type, language_code, country_code) DO NOTHING;

-- Enable Row Level Security
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies for notifications
CREATE POLICY "Users can view their own notifications" ON notifications
    FOR SELECT USING (recipient_id = (current_setting('app.current_user_id'))::bigint);

CREATE POLICY "System can insert notifications" ON notifications
    FOR INSERT WITH CHECK (true);

CREATE POLICY "System can update notifications" ON notifications
    FOR UPDATE USING (true);

-- RLS Policies for notification templates (read-only for users)
CREATE POLICY "Users can view active templates" ON notification_templates
    FOR SELECT USING (is_active = true);

CREATE POLICY "System can manage templates" ON notification_templates
    FOR ALL USING (true);