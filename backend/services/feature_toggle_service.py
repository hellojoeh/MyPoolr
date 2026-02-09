"""Feature toggle service for dynamic feature management."""

import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set
from uuid import UUID
from supabase import Client

from models.feature_toggle import (
    FeatureDefinition, CountryConfig, FeatureToggle, FeatureUsage,
    FeatureScope, ToggleStatus, FeatureContext
)

logger = logging.getLogger(__name__)


class FeatureToggleService:
    """Service for managing dynamic feature toggles."""
    
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._last_cache_update: Optional[datetime] = None
    
    async def is_feature_enabled(
        self,
        feature_name: str,
        context: Optional[FeatureContext] = None
    ) -> bool:
        """
        Check if a feature is enabled for the given context.
        
        Args:
            feature_name: Name of the feature to check
            context: Context for evaluation (user, group, country, etc.)
            
        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            # Get feature definition
            feature_def = await self._get_feature_definition(feature_name)
            if not feature_def:
                logger.warning(f"Feature definition not found: {feature_name}")
                return False
            
            # Check tier requirements
            if feature_def.requires_tier and context and context.tier:
                if not self._check_tier_requirement(feature_def.requires_tier, context.tier):
                    logger.debug(f"Feature {feature_name} requires tier {feature_def.requires_tier}, user has {context.tier}")
                    return False
            
            # Get applicable toggles in priority order
            toggles = await self._get_applicable_toggles(feature_name, context)
            
            # Evaluate toggles (most specific first)
            for toggle in toggles:
                result = self._evaluate_toggle(toggle, context)
                if result is not None:
                    # Track usage if enabled
                    if result and context:
                        await self._track_feature_usage(feature_name, context)
                    return result
            
            # Fall back to feature default
            return feature_def.default_enabled
            
        except Exception as e:
            logger.error(f"Error checking feature {feature_name}: {e}")
            return False
    
    async def get_country_config(self, country_code: str) -> Optional[CountryConfig]:
        """Get configuration for a specific country."""
        try:
            cache_key = f"country_config:{country_code}"
            cached = self._get_from_cache(cache_key)
            if cached:
                return CountryConfig(**cached)
            
            result = self.db.table("country_config").select("*").eq("country_code", country_code).execute()
            
            if result.data:
                config_data = result.data[0]
                self._set_cache(cache_key, config_data)
                return CountryConfig(**config_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting country config for {country_code}: {e}")
            return None
    
    async def update_feature_toggle(
        self,
        feature_name: str,
        scope: FeatureScope,
        scope_value: Optional[str],
        status: ToggleStatus,
        conditions: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Update or create a feature toggle."""
        try:
            toggle_data = {
                "feature_name": feature_name,
                "scope": scope.value,
                "scope_value": scope_value,
                "status": status.value,
                "conditions": conditions or {},
                "expires_at": expires_at.isoformat() if expires_at else None,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert the toggle
            result = self.db.table("feature_toggle").upsert(
                toggle_data,
                on_conflict="feature_name,scope,scope_value"
            ).execute()
            
            if result.data:
                # Clear relevant cache entries
                self._clear_feature_cache(feature_name)
                logger.info(f"Updated feature toggle: {feature_name} {scope.value}:{scope_value} -> {status.value}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating feature toggle {feature_name}: {e}")
            return False
    
    async def get_enabled_features(self, context: FeatureContext) -> Set[str]:
        """Get all enabled features for a given context."""
        try:
            # Get all feature definitions
            result = self.db.table("feature_definition").select("name").execute()
            
            if not result.data:
                return set()
            
            enabled_features = set()
            
            for feature_data in result.data:
                feature_name = feature_data["name"]
                if await self.is_feature_enabled(feature_name, context):
                    enabled_features.add(feature_name)
            
            return enabled_features
            
        except Exception as e:
            logger.error(f"Error getting enabled features: {e}")
            return set()
    
    async def get_feature_usage_stats(
        self,
        feature_name: Optional[str] = None,
        country_code: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get feature usage statistics."""
        try:
            query = self.db.table("feature_usage").select("*")
            
            if feature_name:
                query = query.eq("feature_name", feature_name)
            
            if country_code:
                query = query.eq("country_code", country_code)
            
            # Filter by date range
            cutoff_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            query = query.gte("last_used_at", cutoff_date.isoformat())
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting feature usage stats: {e}")
            return []
    
    async def _get_feature_definition(self, feature_name: str) -> Optional[FeatureDefinition]:
        """Get feature definition from cache or database."""
        cache_key = f"feature_def:{feature_name}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return FeatureDefinition(**cached)
        
        try:
            result = self.db.table("feature_definition").select("*").eq("name", feature_name).execute()
            
            if result.data:
                feature_data = result.data[0]
                self._set_cache(cache_key, feature_data)
                return FeatureDefinition(**feature_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting feature definition {feature_name}: {e}")
            return None
    
    async def _get_applicable_toggles(
        self,
        feature_name: str,
        context: Optional[FeatureContext]
    ) -> List[FeatureToggle]:
        """Get applicable toggles in priority order (most specific first)."""
        try:
            query = self.db.table("feature_toggle").select("*").eq("feature_name", feature_name)
            
            # Filter out expired toggles
            now = datetime.now(timezone.utc).isoformat()
            query = query.or_(f"expires_at.is.null,expires_at.gt.{now}")
            
            result = query.execute()
            
            if not result.data:
                return []
            
            toggles = [FeatureToggle(**toggle_data) for toggle_data in result.data]
            
            # Filter and sort by specificity (most specific first)
            applicable_toggles = []
            
            if context:
                # User-specific toggles (highest priority)
                if context.user_id:
                    user_toggles = [t for t in toggles if t.scope == FeatureScope.USER and t.scope_value == str(context.user_id)]
                    applicable_toggles.extend(user_toggles)
                
                # Group-specific toggles
                if context.mypoolr_id:
                    group_toggles = [t for t in toggles if t.scope == FeatureScope.GROUP and t.scope_value == str(context.mypoolr_id)]
                    applicable_toggles.extend(group_toggles)
                
                # Country-specific toggles
                if context.country_code:
                    country_toggles = [t for t in toggles if t.scope == FeatureScope.COUNTRY and t.scope_value == context.country_code]
                    applicable_toggles.extend(country_toggles)
            
            # Global toggles (lowest priority)
            global_toggles = [t for t in toggles if t.scope == FeatureScope.GLOBAL]
            applicable_toggles.extend(global_toggles)
            
            return applicable_toggles
            
        except Exception as e:
            logger.error(f"Error getting applicable toggles for {feature_name}: {e}")
            return []
    
    def _evaluate_toggle(self, toggle: FeatureToggle, context: Optional[FeatureContext]) -> Optional[bool]:
        """Evaluate a single toggle against context."""
        try:
            # Check if toggle is disabled
            if toggle.status == ToggleStatus.DISABLED:
                return False
            
            # Check if toggle is enabled
            if toggle.status == ToggleStatus.ENABLED:
                return self._check_conditions(toggle, context)
            
            # Handle testing status with percentage rollout
            if toggle.status == ToggleStatus.TESTING:
                if toggle.percentage_rollout is not None:
                    # Use deterministic hash for consistent rollout
                    hash_input = f"{toggle.feature_name}:{context.user_id if context else 'anonymous'}"
                    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
                    percentage = hash_value % 100
                    
                    if percentage < toggle.percentage_rollout:
                        return self._check_conditions(toggle, context)
                    else:
                        return False
                else:
                    # Testing without rollout percentage - treat as enabled for testing
                    return self._check_conditions(toggle, context)
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating toggle {toggle.feature_name}: {e}")
            return None
    
    def _check_conditions(self, toggle: FeatureToggle, context: Optional[FeatureContext]) -> bool:
        """Check if toggle conditions are met."""
        if not toggle.conditions or not context:
            return True
        
        try:
            # Check tier conditions
            if "required_tier" in toggle.conditions:
                required_tier = toggle.conditions["required_tier"]
                if not context.tier or not self._check_tier_requirement(required_tier, context.tier):
                    return False
            
            # Check metadata conditions
            if "metadata" in toggle.conditions and context.metadata:
                required_metadata = toggle.conditions["metadata"]
                for key, value in required_metadata.items():
                    if context.metadata.get(key) != value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking conditions for toggle {toggle.feature_name}: {e}")
            return False
    
    def _check_tier_requirement(self, required_tier: str, user_tier: str) -> bool:
        """Check if user tier meets requirement."""
        tier_hierarchy = ["starter", "essential", "advanced", "extended"]
        
        try:
            required_index = tier_hierarchy.index(required_tier)
            user_index = tier_hierarchy.index(user_tier)
            return user_index >= required_index
        except ValueError:
            return False
    
    async def _track_feature_usage(self, feature_name: str, context: FeatureContext):
        """Track feature usage for analytics."""
        if not context.user_id:
            return
        
        try:
            usage_data = {
                "feature_name": feature_name,
                "user_id": context.user_id,
                "mypoolr_id": str(context.mypoolr_id) if context.mypoolr_id else None,
                "country_code": context.country_code,
                "last_used_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert usage record
            result = self.db.table("feature_usage").upsert(
                usage_data,
                on_conflict="feature_name,user_id,mypoolr_id"
            ).execute()
            
            # Update usage count
            if result.data:
                usage_id = result.data[0]["id"]
                self.db.rpc("increment_usage_count", {"usage_id": usage_id}).execute()
            
        except Exception as e:
            logger.error(f"Error tracking feature usage for {feature_name}: {e}")
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if not self._last_cache_update:
            return None
        
        now = datetime.now(timezone.utc)
        if (now - self._last_cache_update).total_seconds() > self._cache_ttl:
            self._cache.clear()
            self._last_cache_update = None
            return None
        
        return self._cache.get(key)
    
    def _set_cache(self, key: str, value: Any):
        """Set value in cache."""
        self._cache[key] = value
        if not self._last_cache_update:
            self._last_cache_update = datetime.now(timezone.utc)
    
    def _clear_feature_cache(self, feature_name: str):
        """Clear cache entries for a specific feature."""
        keys_to_remove = [key for key in self._cache.keys() if feature_name in key]
        for key in keys_to_remove:
            del self._cache[key]