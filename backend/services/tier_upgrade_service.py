"""Tier upgrade and downgrade service with immediate feature unlocking."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field

from models.mypoolr import TierLevel
from services.tier_management import TierManagementService, TierValidationError
from database import DatabaseManager


class FeatureUnlockResult(BaseModel):
    """Result of feature unlock operation."""
    
    success: bool = Field(..., description="Whether unlock was successful")
    unlocked_features: List[str] = Field(default_factory=list, description="List of unlocked features")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class DowngradeImpact(BaseModel):
    """Impact assessment for tier downgrade."""
    
    affected_groups: List[Dict[str, Any]] = Field(default_factory=list, description="Groups that will be affected")
    features_to_disable: List[str] = Field(default_factory=list, description="Features that will be disabled")
    data_preservation_plan: Dict[str, Any] = Field(default_factory=dict, description="Plan for preserving data")
    requires_user_action: bool = Field(default=False, description="Whether user action is required")
    user_actions: List[str] = Field(default_factory=list, description="Required user actions")


class TierUpgradeDowngradeService:
    """Service for handling tier upgrades and downgrades with feature management."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.tier_service = TierManagementService(db_manager)
    
    async def process_immediate_upgrade(self, admin_id: int, target_tier: TierLevel, payment_reference: str) -> FeatureUnlockResult:
        """Process tier upgrade with immediate feature unlocking."""
        try:
            # Get current tier
            current_tier = await self.tier_service.get_admin_tier(admin_id)
            
            # Validate upgrade
            if not self._is_valid_upgrade(current_tier, target_tier):
                return FeatureUnlockResult(
                    success=False,
                    errors=[f"Invalid upgrade from {current_tier} to {target_tier}"]
                )
            
            # Process the tier upgrade
            upgrade_success = await self.tier_service.process_tier_upgrade(admin_id, target_tier, payment_reference)
            
            if not upgrade_success:
                return FeatureUnlockResult(
                    success=False,
                    errors=["Failed to process tier upgrade"]
                )
            
            # Unlock features immediately
            unlocked_features = await self._unlock_tier_features(admin_id, current_tier, target_tier)
            
            # Update admin's groups with new tier capabilities
            await self._update_admin_groups_tier(admin_id, target_tier)
            
            # Log the upgrade
            await self._log_tier_change(admin_id, current_tier, target_tier, "upgrade", payment_reference)
            
            return FeatureUnlockResult(
                success=True,
                unlocked_features=unlocked_features
            )
            
        except Exception as e:
            return FeatureUnlockResult(
                success=False,
                errors=[f"Upgrade processing failed: {str(e)}"]
            )
    
    async def assess_downgrade_impact(self, admin_id: int, target_tier: TierLevel) -> DowngradeImpact:
        """Assess the impact of downgrading to a target tier."""
        try:
            current_tier = await self.tier_service.get_admin_tier(admin_id)
            current_features = self.tier_service.get_tier_features(current_tier)
            target_features = self.tier_service.get_tier_features(target_tier)
            
            # Get admin's groups
            admin_groups = await self._get_admin_groups(admin_id)
            
            # Assess impact on groups
            affected_groups = []
            features_to_disable = []
            user_actions = []
            
            # Check group count limits
            if len(admin_groups) > target_features.max_groups:
                excess_groups = len(admin_groups) - target_features.max_groups
                affected_groups.extend([
                    {
                        "id": group["id"],
                        "name": group["name"],
                        "reason": "Exceeds group limit",
                        "action_required": "Archive or transfer ownership"
                    }
                    for group in admin_groups[-excess_groups:]  # Last created groups
                ])
                user_actions.append(f"Archive or transfer {excess_groups} groups")
            
            # Check member limits per group
            for group in admin_groups:
                member_count = await self._count_group_members(UUID(group["id"]))
                if member_count > target_features.max_members_per_group:
                    affected_groups.append({
                        "id": group["id"],
                        "name": group["name"],
                        "reason": f"Has {member_count} members, limit is {target_features.max_members_per_group}",
                        "action_required": "Remove excess members"
                    })
                    user_actions.append(f"Remove {member_count - target_features.max_members_per_group} members from {group['name']}")
            
            # Check feature downgrades
            if current_features.advanced_analytics and not target_features.advanced_analytics:
                features_to_disable.append("Advanced Analytics")
            
            if current_features.export_data and not target_features.export_data:
                features_to_disable.append("Data Export")
            
            if current_features.bulk_member_management and not target_features.bulk_member_management:
                features_to_disable.append("Bulk Member Management")
            
            if current_features.custom_rotation_schedules and not target_features.custom_rotation_schedules:
                features_to_disable.append("Custom Rotation Schedules")
            
            if current_features.priority_support and not target_features.priority_support:
                features_to_disable.append("Priority Support")
            
            return DowngradeImpact(
                affected_groups=affected_groups,
                features_to_disable=features_to_disable,
                data_preservation_plan={
                    "analytics_data": "Preserved but not accessible",
                    "export_history": "Preserved but new exports disabled",
                    "custom_schedules": "Converted to standard schedules"
                },
                requires_user_action=len(user_actions) > 0,
                user_actions=user_actions
            )
            
        except Exception as e:
            return DowngradeImpact(
                affected_groups=[],
                features_to_disable=[],
                data_preservation_plan={},
                requires_user_action=False,
                user_actions=[f"Error assessing impact: {str(e)}"]
            )
    
    async def process_graceful_downgrade(self, admin_id: int, target_tier: TierLevel, preserve_data: bool = True) -> FeatureUnlockResult:
        """Process tier downgrade with data preservation."""
        try:
            current_tier = await self.tier_service.get_admin_tier(admin_id)
            
            # Assess downgrade impact
            impact = await self.assess_downgrade_impact(admin_id, target_tier)
            
            # If user action is required and we haven't handled it, return error
            if impact.requires_user_action:
                return FeatureUnlockResult(
                    success=False,
                    errors=["User action required before downgrade"] + impact.user_actions
                )
            
            # Process the tier downgrade
            downgrade_success = await self.tier_service.handle_tier_downgrade(admin_id)
            
            if downgrade_success != target_tier:
                return FeatureUnlockResult(
                    success=False,
                    errors=[f"Downgrade resulted in {downgrade_success} instead of {target_tier}"]
                )
            
            # Disable features gracefully
            disabled_features = await self._disable_tier_features(admin_id, current_tier, target_tier, preserve_data)
            
            # Update admin's groups with new tier limitations
            await self._update_admin_groups_tier(admin_id, target_tier)
            
            # Log the downgrade
            await self._log_tier_change(admin_id, current_tier, target_tier, "downgrade")
            
            return FeatureUnlockResult(
                success=True,
                unlocked_features=disabled_features  # Actually disabled features
            )
            
        except Exception as e:
            return FeatureUnlockResult(
                success=False,
                errors=[f"Downgrade processing failed: {str(e)}"]
            )
    
    async def handle_subscription_expiry(self, admin_id: int) -> FeatureUnlockResult:
        """Handle subscription expiry with automatic downgrade."""
        try:
            # Check if subscription has actually expired
            is_expired = await self.tier_service.check_subscription_expiry(admin_id)
            
            if not is_expired:
                return FeatureUnlockResult(
                    success=False,
                    errors=["Subscription has not expired"]
                )
            
            # Determine appropriate downgrade tier
            current_tier = await self.tier_service.get_admin_tier(admin_id)
            
            # Downgrade to Starter for expired subscriptions
            target_tier = TierLevel.STARTER
            
            # Process graceful downgrade
            result = await self.process_graceful_downgrade(admin_id, target_tier, preserve_data=True)
            
            if result.success:
                # Send notification about expiry and downgrade
                await self._notify_subscription_expiry(admin_id, current_tier, target_tier)
            
            return result
            
        except Exception as e:
            return FeatureUnlockResult(
                success=False,
                errors=[f"Subscription expiry handling failed: {str(e)}"]
            )
    
    async def _unlock_tier_features(self, admin_id: int, from_tier: TierLevel, to_tier: TierLevel) -> List[str]:
        """Unlock features when upgrading tiers."""
        from_features = self.tier_service.get_tier_features(from_tier)
        to_features = self.tier_service.get_tier_features(to_tier)
        
        unlocked_features = []
        
        # Check each feature for unlock
        if not from_features.advanced_analytics and to_features.advanced_analytics:
            unlocked_features.append("Advanced Analytics")
            await self._enable_analytics(admin_id)
        
        if not from_features.export_data and to_features.export_data:
            unlocked_features.append("Data Export")
            await self._enable_data_export(admin_id)
        
        if not from_features.bulk_member_management and to_features.bulk_member_management:
            unlocked_features.append("Bulk Member Management")
            await self._enable_bulk_operations(admin_id)
        
        if not from_features.custom_rotation_schedules and to_features.custom_rotation_schedules:
            unlocked_features.append("Custom Rotation Schedules")
            await self._enable_custom_schedules(admin_id)
        
        if not from_features.priority_support and to_features.priority_support:
            unlocked_features.append("Priority Support")
            await self._enable_priority_support(admin_id)
        
        return unlocked_features
    
    async def _disable_tier_features(self, admin_id: int, from_tier: TierLevel, to_tier: TierLevel, preserve_data: bool) -> List[str]:
        """Disable features when downgrading tiers."""
        from_features = self.tier_service.get_tier_features(from_tier)
        to_features = self.tier_service.get_tier_features(to_tier)
        
        disabled_features = []
        
        # Check each feature for disable
        if from_features.advanced_analytics and not to_features.advanced_analytics:
            disabled_features.append("Advanced Analytics")
            await self._disable_analytics(admin_id, preserve_data)
        
        if from_features.export_data and not to_features.export_data:
            disabled_features.append("Data Export")
            await self._disable_data_export(admin_id, preserve_data)
        
        if from_features.bulk_member_management and not to_features.bulk_member_management:
            disabled_features.append("Bulk Member Management")
            await self._disable_bulk_operations(admin_id, preserve_data)
        
        if from_features.custom_rotation_schedules and not to_features.custom_rotation_schedules:
            disabled_features.append("Custom Rotation Schedules")
            await self._disable_custom_schedules(admin_id, preserve_data)
        
        if from_features.priority_support and not to_features.priority_support:
            disabled_features.append("Priority Support")
            await self._disable_priority_support(admin_id)
        
        return disabled_features
    
    async def _update_admin_groups_tier(self, admin_id: int, new_tier: TierLevel):
        """Update all admin's groups with new tier information."""
        try:
            await self.db.client.table("mypoolrs").update({
                "tier": new_tier.value,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("admin_id", admin_id).execute()
        except Exception as e:
            print(f"Error updating admin groups tier: {e}")
    
    async def _get_admin_groups(self, admin_id: int) -> List[Dict[str, Any]]:
        """Get all groups owned by admin."""
        try:
            result = await self.db.client.table("mypoolrs").select("*").eq("admin_id", admin_id).eq("status", "active").execute()
            return result.data or []
        except Exception:
            return []
    
    async def _count_group_members(self, group_id: UUID) -> int:
        """Count members in a group."""
        try:
            result = await self.db.client.table("members").select("id", count="exact").eq("mypoolr_id", str(group_id)).eq("status", "active").execute()
            return result.count or 0
        except Exception:
            return 0
    
    async def _log_tier_change(self, admin_id: int, from_tier: TierLevel, to_tier: TierLevel, change_type: str, payment_reference: str = None):
        """Log tier change for audit purposes."""
        try:
            log_data = {
                "admin_id": admin_id,
                "from_tier": from_tier.value,
                "to_tier": to_tier.value,
                "change_type": change_type,
                "payment_reference": payment_reference,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.db.client.table("tier_change_logs").insert(log_data).execute()
        except Exception as e:
            print(f"Error logging tier change: {e}")
    
    # Feature-specific enable/disable methods
    async def _enable_analytics(self, admin_id: int):
        """Enable analytics features for admin."""
        # Implementation would enable analytics data collection and UI
        pass
    
    async def _disable_analytics(self, admin_id: int, preserve_data: bool):
        """Disable analytics features for admin."""
        # Implementation would hide analytics UI but preserve data if requested
        pass
    
    async def _enable_data_export(self, admin_id: int):
        """Enable data export features for admin."""
        # Implementation would enable export functionality
        pass
    
    async def _disable_data_export(self, admin_id: int, preserve_data: bool):
        """Disable data export features for admin."""
        # Implementation would disable export functionality
        pass
    
    async def _enable_bulk_operations(self, admin_id: int):
        """Enable bulk operations for admin."""
        # Implementation would enable bulk member management UI
        pass
    
    async def _disable_bulk_operations(self, admin_id: int, preserve_data: bool):
        """Disable bulk operations for admin."""
        # Implementation would disable bulk operations UI
        pass
    
    async def _enable_custom_schedules(self, admin_id: int):
        """Enable custom rotation schedules for admin."""
        # Implementation would enable custom schedule UI
        pass
    
    async def _disable_custom_schedules(self, admin_id: int, preserve_data: bool):
        """Disable custom rotation schedules for admin."""
        # Implementation would convert custom schedules to standard ones
        pass
    
    async def _enable_priority_support(self, admin_id: int):
        """Enable priority support for admin."""
        # Implementation would flag admin for priority support
        pass
    
    async def _disable_priority_support(self, admin_id: int):
        """Disable priority support for admin."""
        # Implementation would remove priority support flag
        pass
    
    async def _notify_subscription_expiry(self, admin_id: int, from_tier: TierLevel, to_tier: TierLevel):
        """Send notification about subscription expiry and downgrade."""
        # Implementation would send notification via Telegram bot
        pass
    
    def _is_valid_upgrade(self, current_tier: TierLevel, target_tier: TierLevel) -> bool:
        """Check if upgrade path is valid."""
        tier_order = [TierLevel.STARTER, TierLevel.ESSENTIAL, TierLevel.ADVANCED, TierLevel.EXTENDED]
        current_index = tier_order.index(current_tier)
        target_index = tier_order.index(target_tier)
        
        return target_index > current_index