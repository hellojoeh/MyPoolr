"""Decorators for feature toggle enforcement."""

import functools
import logging
from typing import Callable, Optional, Any
from fastapi import HTTPException, status

from models.feature_toggle import FeatureContext
from .feature_toggle_service import FeatureToggleService

logger = logging.getLogger(__name__)


def require_feature(
    feature_name: str,
    context_extractor: Optional[Callable] = None,
    error_message: Optional[str] = None
):
    """
    Decorator to require a feature to be enabled.
    
    Args:
        feature_name: Name of the required feature
        context_extractor: Function to extract FeatureContext from request
        error_message: Custom error message if feature is disabled
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get feature toggle service (assume it's available in app state)
            # This would typically be injected via dependency injection
            feature_service = kwargs.get('feature_service')
            if not feature_service:
                logger.warning(f"Feature service not available for {feature_name} check")
                # In production, you might want to fail closed (return False)
                # For now, we'll allow the request to proceed
                return await func(*args, **kwargs)
            
            # Extract context
            context = None
            if context_extractor:
                try:
                    context = context_extractor(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error extracting context for feature {feature_name}: {e}")
                    context = FeatureContext()
            else:
                context = FeatureContext()
            
            # Check if feature is enabled
            is_enabled = await feature_service.is_feature_enabled(feature_name, context)
            
            if not is_enabled:
                error_msg = error_message or f"Feature '{feature_name}' is not available"
                logger.info(f"Feature {feature_name} blocked for context: {context.to_dict()}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def feature_flag(
    feature_name: str,
    context_extractor: Optional[Callable] = None,
    default_value: Any = None
):
    """
    Decorator to conditionally execute code based on feature flag.
    
    Args:
        feature_name: Name of the feature flag
        context_extractor: Function to extract FeatureContext from request
        default_value: Value to return if feature is disabled
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get feature toggle service
            feature_service = kwargs.get('feature_service')
            if not feature_service:
                logger.warning(f"Feature service not available for {feature_name} check")
                return await func(*args, **kwargs)
            
            # Extract context
            context = None
            if context_extractor:
                try:
                    context = context_extractor(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error extracting context for feature {feature_name}: {e}")
                    context = FeatureContext()
            else:
                context = FeatureContext()
            
            # Check if feature is enabled
            is_enabled = await feature_service.is_feature_enabled(feature_name, context)
            
            if is_enabled:
                return await func(*args, **kwargs)
            else:
                logger.debug(f"Feature {feature_name} disabled, returning default value")
                return default_value
        
        return wrapper
    return decorator


class FeatureGate:
    """Context manager for feature-gated code blocks."""
    
    def __init__(
        self,
        feature_service: FeatureToggleService,
        feature_name: str,
        context: Optional[FeatureContext] = None
    ):
        self.feature_service = feature_service
        self.feature_name = feature_name
        self.context = context or FeatureContext()
        self.is_enabled = False
    
    async def __aenter__(self):
        """Check if feature is enabled when entering context."""
        self.is_enabled = await self.feature_service.is_feature_enabled(
            self.feature_name, 
            self.context
        )
        return self.is_enabled
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting context."""
        pass


# Common context extractors
def extract_user_context(request, **kwargs) -> FeatureContext:
    """Extract user context from FastAPI request."""
    # This would typically extract user info from JWT token or session
    user_id = getattr(request.state, 'user_id', None)
    country_code = getattr(request.state, 'country_code', None)
    tier = getattr(request.state, 'tier', None)
    
    return FeatureContext(
        user_id=user_id,
        country_code=country_code,
        tier=tier
    )


def extract_mypoolr_context(mypoolr_id: str, **kwargs) -> FeatureContext:
    """Extract MyPoolr context from path parameter."""
    # This would typically also include user context
    return FeatureContext(
        mypoolr_id=mypoolr_id,
        # Add user context from request if available
    )


# Example usage decorators
def require_payment_integration(func: Callable) -> Callable:
    """Require payment integration feature to be enabled."""
    return require_feature(
        "payment_integration",
        context_extractor=extract_user_context,
        error_message="Payment features are not available in your region"
    )(func)


def require_multi_group_creation(func: Callable) -> Callable:
    """Require multi-group creation feature to be enabled."""
    return require_feature(
        "multi_group_creation",
        context_extractor=extract_user_context,
        error_message="Multiple group creation requires a tier upgrade"
    )(func)


def require_advanced_notifications(func: Callable) -> Callable:
    """Require advanced notifications feature to be enabled."""
    return require_feature(
        "advanced_notifications",
        context_extractor=extract_user_context,
        error_message="Advanced notifications require a tier upgrade"
    )(func)