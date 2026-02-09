"""Integration tests for MyPoolr Circles component wiring."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from integration import IntegrationManager
from services.payment_interface import PaymentServiceRegistry
from services.tier_management import TierManagementService
from services.notification_service import NotificationService


class TestIntegrationManager:
    """Test the integration manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.integration_manager = IntegrationManager()
        
        # Mock dependencies
        self.integration_manager.db_manager = Mock()
        self.integration_manager.payment_registry = Mock(spec=PaymentServiceRegistry)
        self.integration_manager.tier_service = Mock(spec=TierManagementService)
        self.integration_manager.notification_service = Mock(spec=NotificationService)
    
    @pytest.mark.asyncio
    async def test_mypoolr_creation_with_tier_validation(self):
        """Test MyPoolr creation with tier validation."""
        # Setup mocks
        self.integration_manager.tier_service.validate_tier_limits = AsyncMock(return_value=True)
        self.integration_manager.db_manager.client.table.return_value.insert.return_value.execute = AsyncMock(
            return_value=Mock(data=[{"id": "test-id", "name": "Test Group"}])
        )
        
        # Test data
        mypoolr_data = {
            "admin_id": 12345,
            "name": "Test Group",
            "contribution_amount": 1000.0,
            "rotation_frequency": "weekly",
            "member_limit": 10
        }
        
        # Execute
        result = await self.integration_manager.handle_mypoolr_creation(mypoolr_data)
        
        # Verify
        assert result["success"] is True
        assert "mypoolr" in result
        self.integration_manager.tier_service.validate_tier_limits.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mypoolr_creation_tier_limit_exceeded(self):
        """Test MyPoolr creation when tier limit is exceeded."""
        # Setup mocks
        self.integration_manager.tier_service.validate_tier_limits = AsyncMock(return_value=False)
        self.integration_manager.tier_service.get_admin_tier = AsyncMock(return_value="starter")
        self.integration_manager.tier_service.get_tier_info = Mock(return_value={
            "name": "Starter",
            "features": Mock(max_groups=1)
        })
        
        # Test data
        mypoolr_data = {
            "admin_id": 12345,
            "name": "Test Group",
            "contribution_amount": 1000.0,
            "rotation_frequency": "weekly",
            "member_limit": 10
        }
        
        # Execute
        result = await self.integration_manager.handle_mypoolr_creation(mypoolr_data)
        
        # Verify
        assert result["success"] is False
        assert result["error"] == "tier_limit_exceeded"
        assert result["upgrade_required"] is True
    
    @pytest.mark.asyncio
    async def test_member_join_with_capacity_validation(self):
        """Test member joining with capacity validation."""
        # Setup mocks
        self.integration_manager.db_manager.client.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
            return_value=Mock(data=[{"id": "mypoolr-id", "admin_id": 12345}])
        )
        self.integration_manager.tier_service.validate_tier_limits = AsyncMock(return_value=True)
        self.integration_manager.db_manager.client.table.return_value.insert.return_value.execute = AsyncMock(
            return_value=Mock(data=[{"id": "member-id", "name": "Test Member"}])
        )
        
        # Test data
        join_data = {
            "mypoolr_id": "mypoolr-id",
            "telegram_id": 67890,
            "name": "Test Member",
            "phone_number": "+254700000000",
            "security_deposit_amount": 5000.0
        }
        
        # Execute
        result = await self.integration_manager.handle_member_join(join_data)
        
        # Verify
        assert result["success"] is True
        assert "member" in result
    
    @pytest.mark.asyncio
    async def test_contribution_confirmation_with_advancement(self):
        """Test contribution confirmation with rotation advancement."""
        # Setup mocks
        self.integration_manager.db_manager.client.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
            return_value=Mock(data=[{
                "id": "transaction-id",
                "sender_confirmed_at": "2024-01-01T00:00:00Z",
                "recipient_confirmed_at": "2024-01-01T00:00:00Z",
                "mypoolr_id": "mypoolr-id"
            }])
        )
        
        # Mock rotation advancement check
        self.integration_manager._check_rotation_advancement = AsyncMock()
        
        # Test data
        confirmation_data = {
            "transaction_id": "transaction-id",
            "confirmer_type": "sender"
        }
        
        # Execute
        result = await self.integration_manager.handle_contribution_confirmation(confirmation_data)
        
        # Verify
        assert result["success"] is True
        assert result["status"] == "completed"
        self.integration_manager._check_rotation_advancement.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tier_upgrade_payment_processing(self):
        """Test tier upgrade payment processing."""
        # Setup mocks
        mock_provider = Mock()
        mock_provider.initiate_payment = AsyncMock(return_value=Mock(
            payment_id="payment-123",
            status=Mock(value="pending"),
            amount=500.0,
            currency="KES",
            checkout_url="https://checkout.example.com",
            expires_at=datetime.utcnow()
        ))
        
        self.integration_manager.payment_registry.get_provider_for_country = Mock(return_value=mock_provider)
        self.integration_manager.tier_service.get_tier_pricing = Mock(return_value=Mock(
            monthly_price=500.0,
            currency="KES"
        ))
        self.integration_manager.db_manager.client.table.return_value.insert.return_value.execute = AsyncMock()
        
        # Test data
        payment_data = {
            "admin_id": 12345,
            "target_tier": "essential",
            "phone_number": "+254700000000"
        }
        
        # Execute
        result = await self.integration_manager.handle_tier_upgrade_payment(payment_data)
        
        # Verify
        assert result["success"] is True
        assert result["payment_id"] == "payment-123"
        assert result["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_payment_callback_processing(self):
        """Test payment callback processing."""
        # Setup mocks
        mock_provider = Mock()
        mock_provider.handle_callback = AsyncMock(return_value=Mock(
            success=True,
            payment_id="payment-123",
            status=Mock(value="completed"),
            message="Payment completed"
        ))
        
        self.integration_manager.payment_registry.get_provider = Mock(return_value=mock_provider)
        self.integration_manager.db_manager.client.table.return_value.update.return_value.eq.return_value.execute = AsyncMock()
        self.integration_manager._process_completed_tier_payment = AsyncMock()
        
        # Test data
        callback_data = {
            "payment_id": "payment-123",
            "status": "completed"
        }
        
        # Execute
        result = await self.integration_manager.handle_payment_callback("mpesa", callback_data)
        
        # Verify
        assert result["success"] is True
        assert result["payment_id"] == "payment-123"
        assert result["status"] == "completed"
        self.integration_manager._process_completed_tier_payment.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_system_status_check(self):
        """Test system status check."""
        # Setup mocks
        self.integration_manager._initialized = True
        self.integration_manager.db_manager.client.table.return_value.select.return_value.limit.return_value.execute = AsyncMock()
        self.integration_manager.payment_registry.list_providers = Mock(return_value=["mpesa"])
        self.integration_manager.notification_service.templates = {"test": "template"}
        
        # Execute
        status = await self.integration_manager.get_system_status()
        
        # Verify
        assert status["integration_initialized"] is True
        assert status["database_connected"] is True
        assert "mpesa" in status["payment_providers"]
        assert status["notification_system"] is True


def test_integration_manager_initialization():
    """Test integration manager initialization."""
    manager = IntegrationManager()
    
    assert manager.db_manager is not None
    assert manager.payment_registry is not None
    assert manager.tier_service is not None
    assert manager.notification_service is not None
    assert manager._initialized is False


@pytest.mark.asyncio
async def test_integration_initialization():
    """Test full integration initialization."""
    manager = IntegrationManager()
    
    # Mock all initialization methods
    manager._initialize_database = AsyncMock()
    manager._initialize_payment_services = AsyncMock()
    manager._initialize_notification_system = AsyncMock()
    manager._initialize_task_monitoring = AsyncMock()
    
    # Execute
    await manager.initialize()
    
    # Verify
    assert manager._initialized is True
    manager._initialize_database.assert_called_once()
    manager._initialize_payment_services.assert_called_once()
    manager._initialize_notification_system.assert_called_once()
    manager._initialize_task_monitoring.assert_called_once()


if __name__ == "__main__":
    # Run a simple integration test
    async def simple_test():
        manager = IntegrationManager()
        
        # Mock the database manager
        manager.db_manager = Mock()
        manager.db_manager.client.table.return_value.select.return_value.limit.return_value.execute = AsyncMock()
        
        # Test system status
        status = await manager.get_system_status()
        print(f"Integration status: {status}")
        
        print("✅ Basic integration test passed")
    
    asyncio.run(simple_test())