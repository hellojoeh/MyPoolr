"""Backend API client for MyPoolr Telegram Bot."""

import httpx
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime

from config import config


class BackendClient:
    """Client for communicating with MyPoolr backend API."""
    
    def __init__(self):
        self.base_url = config.backend_api_url
        self.api_key = config.backend_api_key
        self.timeout = 30.0
        self._session: Optional[httpx.AsyncClient] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MyPoolr-TelegramBot/1.0",
            "X-Request-Source": "telegram_bot",
            "X-Request-Timestamp": datetime.utcnow().isoformat()
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._get_headers()
            )
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.is_closed:
            await self._session.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """Make HTTP request to backend API with retry logic."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        max_retries = 3
        
        try:
            session = await self._get_session()
            response = await session.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text}")
            
            # Handle specific error cases
            if e.response.status_code == 429 and retry_count < max_retries:
                # Rate limited, retry with backoff
                import asyncio
                await asyncio.sleep(2 ** retry_count)
                return await self._make_request(method, endpoint, data, params, retry_count + 1)
            
            # Return structured error response
            try:
                error_data = e.response.json()
                return {
                    "success": False,
                    "error": error_data.get("error", "http_error"),
                    "message": error_data.get("message", f"HTTP {e.response.status_code}"),
                    "status_code": e.response.status_code
                }
            except:
                return {
                    "success": False,
                    "error": "http_error",
                    "message": f"HTTP {e.response.status_code}: {e.response.text}",
                    "status_code": e.response.status_code
                }
        
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {url}: {e}")
            
            # Retry on network errors
            if retry_count < max_retries:
                import asyncio
                await asyncio.sleep(2 ** retry_count)
                return await self._make_request(method, endpoint, data, params, retry_count + 1)
            
            return {
                "success": False,
                "error": "network_error",
                "message": f"Network error: {str(e)}"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            return {
                "success": False,
                "error": "unexpected_error",
                "message": f"Unexpected error: {str(e)}"
            }
    
    # MyPoolr operations
    async def create_mypoolr(self, mypoolr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new MyPoolr group."""
        return await self._make_request("POST", "/mypoolr/create", data=mypoolr_data)
    
    async def get_mypoolr(self, mypoolr_id: str) -> Dict[str, Any]:
        """Get MyPoolr group details."""
        return await self._make_request("GET", f"/mypoolr/{mypoolr_id}")
    
    async def get_user_mypoolrs(self, user_id: int) -> Dict[str, Any]:
        """Get user's MyPoolr groups."""
        try:
            result = await self._make_request("GET", f"/mypoolr/admin/{user_id}")
            
            # Handle error responses
            if isinstance(result, dict) and not result.get("success", True):
                return result
            
            # Backend returns a list directly on success
            if isinstance(result, list):
                return {
                    "success": True,
                    "groups": result
                }
            
            # Unexpected format
            return {
                "success": False,
                "error": "invalid_response",
                "message": "Unexpected response format from backend"
            }
        except Exception as e:
            logger.error(f"Error getting user mypoolrs: {e}")
            return {
                "success": False,
                "error": "exception",
                "message": str(e)
            }
    
    async def get_member_groups(self, user_id: int) -> Dict[str, Any]:
        """Get groups where user is a member."""
        # This would need a backend endpoint to get member's groups
        # For now, return the admin groups as a fallback
        return await self.get_user_mypoolrs(user_id)
    
    async def get_mypoolr_details(self, mypoolr_id: str) -> Dict[str, Any]:
        """Get detailed MyPoolr information."""
        return await self.get_mypoolr(mypoolr_id)
    
    async def validate_invitation(self, invitation_code: str) -> Dict[str, Any]:
        """Validate an invitation code."""
        return await self._make_request("POST", "/mypoolr/invitation/validate", data={
            "token": invitation_code
        })
    
    async def link_telegram_group(
        self,
        mypoolr_id: str,
        telegram_group_id: int,
        telegram_group_name: str,
        linked_by: int
    ) -> Dict[str, Any]:
        """Link a Telegram group to a MyPoolr."""
        return await self._make_request("POST", f"/mypoolr/{mypoolr_id}/link-telegram", data={
            "telegram_group_id": telegram_group_id,
            "telegram_group_name": telegram_group_name,
            "linked_by": linked_by
        })
    
    # Member operations
    async def join_mypoolr(self, join_data: Dict[str, Any]) -> Dict[str, Any]:
        """Join a MyPoolr group."""
        return await self._make_request("POST", "/member/join", data=join_data)
    
    async def get_member_details(self, member_id: str) -> Dict[str, Any]:
        """Get member details."""
        return await self._make_request("GET", f"/member/{member_id}")
    
    # Contribution operations
    async def confirm_contribution(self, contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Confirm a contribution."""
        return await self._make_request("POST", "/contribution/confirm", data=contribution_data)
    
    async def get_pending_contributions(self, user_id: int) -> Dict[str, Any]:
        """Get pending contributions for user."""
        return await self._make_request("GET", f"/user/{user_id}/contributions/pending")
    
    # Tier operations
    async def upgrade_tier(self, upgrade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upgrade user tier."""
        return await self._make_request("POST", "/tier/upgrade", data=upgrade_data)
    
    async def get_tier_info(self, tier_id: str) -> Dict[str, Any]:
        """Get tier information."""
        return await self._make_request("GET", f"/tier/{tier_id}")
    
    # Utility operations
    async def health_check(self) -> Dict[str, Any]:
        """Check backend API health."""
        return await self._make_request("GET", "/health")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return await self._make_request("GET", "/system/integration/status")
    
    # Enhanced MyPoolr operations with tier validation
    async def create_mypoolr_with_validation(self, mypoolr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create MyPoolr with tier validation and notifications."""
        return await self._make_request("POST", "/integration/mypoolr/create", data=mypoolr_data)
    
    async def get_admin_tier_info(self, admin_id: int) -> Dict[str, Any]:
        """Get admin's current tier and feature limits."""
        return await self._make_request("GET", f"/tier/admin/{admin_id}/info")
    
    async def get_tier_comparison(self) -> Dict[str, Any]:
        """Get comparison of all available tiers."""
        return await self._make_request("GET", "/tier/comparison")
    
    # Enhanced member operations
    async def join_mypoolr_with_validation(self, join_data: Dict[str, Any]) -> Dict[str, Any]:
        """Join MyPoolr with capacity validation and notifications."""
        return await self._make_request("POST", "/integration/member/join", data=join_data)
    
    async def get_member_security_status(self, member_id: str) -> Dict[str, Any]:
        """Get member's security deposit and lock-in status."""
        return await self._make_request("GET", f"/member/{member_id}/security")
    
    # Enhanced contribution operations
    async def confirm_contribution_with_advancement(self, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Confirm contribution with automatic rotation advancement."""
        return await self._make_request("POST", "/integration/contribution/confirm", data=confirmation_data)
    
    async def get_rotation_status(self, mypoolr_id: str) -> Dict[str, Any]:
        """Get current rotation status and pending contributions."""
        return await self._make_request("GET", f"/mypoolr/{mypoolr_id}/rotation/status")
    
    # Payment and tier upgrade operations
    async def initiate_tier_upgrade_payment(self, upgrade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate tier upgrade payment."""
        return await self._make_request("POST", "/integration/tier/upgrade/payment", data=upgrade_data)
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status."""
        return await self._make_request("GET", f"/payment/{payment_id}/status")
    
    # Notification operations
    async def get_user_notifications(self, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get recent notifications for user."""
        return await self._make_request("GET", f"/user/{user_id}/notifications", params={"limit": limit})
    
    async def mark_notification_read(self, notification_id: str) -> Dict[str, Any]:
        """Mark notification as read."""
        return await self._make_request("POST", f"/notification/{notification_id}/read")
    
    # Analytics and reporting
    async def get_mypoolr_analytics(self, mypoolr_id: str) -> Dict[str, Any]:
        """Get MyPoolr analytics (tier-restricted)."""
        return await self._make_request("GET", f"/mypoolr/{mypoolr_id}/analytics")
    
    async def export_mypoolr_data(self, mypoolr_id: str, format: str = "json") -> Dict[str, Any]:
        """Export MyPoolr data (tier-restricted)."""
        return await self._make_request("GET", f"/mypoolr/{mypoolr_id}/export", params={"format": format})
    
    # Bulk operations (tier-restricted)
    async def bulk_member_operation(self, mypoolr_id: str, operation: str, member_ids: List[str]) -> Dict[str, Any]:
        """Perform bulk member operations (tier-restricted)."""
        return await self._make_request("POST", f"/mypoolr/{mypoolr_id}/members/bulk", data={
            "operation": operation,
            "member_ids": member_ids
        })
    
    # Error handling and recovery
    async def report_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Report error to backend for monitoring."""
        return await self._make_request("POST", "/system/error/report", data=error_data)
    
    async def get_recovery_suggestions(self, error_type: str) -> Dict[str, Any]:
        """Get recovery suggestions for error type."""
        return await self._make_request("GET", f"/system/recovery/suggestions/{error_type}")
    
    # Feature toggle operations
    async def get_enabled_features(self, country: str = None, mypoolr_id: str = None) -> Dict[str, Any]:
        """Get enabled features for context."""
        params = {}
        if country:
            params["country"] = country
        if mypoolr_id:
            params["mypoolr_id"] = mypoolr_id
        
        return await self._make_request("GET", "/features/enabled", params=params)
    
    async def is_feature_enabled(self, feature: str, country: str = None, mypoolr_id: str = None) -> bool:
        """Check if specific feature is enabled."""
        params = {"feature": feature}
        if country:
            params["country"] = country
        if mypoolr_id:
            params["mypoolr_id"] = mypoolr_id
        
        result = await self._make_request("GET", "/features/check", params=params)
        return result.get("enabled", False) if result.get("success", False) else False

    # Additional methods for callback handlers
    async def get_pending_deposits(self, user_id: int) -> Dict[str, Any]:
        """Get pending security deposits for a user."""
        return await self._make_request("GET", f"/members/{user_id}/pending-deposits")
    
    async def get_deposit_details(self, deposit_id: str) -> Dict[str, Any]:
        """Get details for a specific security deposit."""
        return await self._make_request("GET", f"/deposits/{deposit_id}")
    
    async def get_full_report(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive report for a user."""
        return await self._make_request("GET", f"/members/{user_id}/full-report")
    
    async def generate_report(self, user_id: int, format_type: str) -> Dict[str, Any]:
        """Generate and export a report in specified format."""
        return await self._make_request("POST", f"/members/{user_id}/export-report", 
                                       json={"format": format_type})

    
    # Tier and trial operations
    async def activate_trial(self, user_id: int, tier: str) -> Dict[str, Any]:
        """Activate a free trial for a tier."""
        try:
            result = await self._make_request("POST", "/tier/trial/activate", data={
                "user_id": user_id,
                "tier": tier
            })
            
            # Handle error responses
            if isinstance(result, dict) and not result.get("success", True):
                return result
            
            # Success response
            if isinstance(result, dict) and result.get("success"):
                return result
            
            # Unexpected format
            return {
                "success": False,
                "error": "invalid_response",
                "message": "Unexpected response format from backend"
            }
        except Exception as e:
            logger.error(f"Error activating trial: {e}")
            return {
                "success": False,
                "error": "exception",
                "message": str(e)
            }
    
    async def get_trial_status(self, user_id: int) -> Dict[str, Any]:
        """Get trial status for a user."""
        try:
            result = await self._make_request("GET", f"/tier/trial/status/{user_id}")
            
            # Handle error responses
            if isinstance(result, dict) and not result.get("success", True):
                return result
            
            # Success response
            if isinstance(result, dict):
                return {
                    "success": True,
                    **result
                }
            
            # Unexpected format
            return {
                "success": False,
                "error": "invalid_response",
                "message": "Unexpected response format from backend"
            }
        except Exception as e:
            logger.error(f"Error getting trial status: {e}")
            return {
                "success": False,
                "error": "exception",
                "message": str(e)
            }
