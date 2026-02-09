"""Simple integration test to verify component wiring."""

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def test_integration_manager_creation():
    """Test that IntegrationManager can be created."""
    try:
        from integration import IntegrationManager
        
        # Create manager
        manager = IntegrationManager()
        
        # Check basic attributes exist
        assert hasattr(manager, 'db_manager')
        assert hasattr(manager, 'payment_registry')
        assert hasattr(manager, 'tier_service')
        assert hasattr(manager, '_initialized')
        
        print("✅ IntegrationManager creation test passed")
        return True
        
    except Exception as e:
        print(f"❌ IntegrationManager creation test failed: {e}")
        return False

def test_payment_service_registry():
    """Test payment service registry functionality."""
    try:
        from services.payment_interface import PaymentServiceRegistry, PaymentServiceInterface
        from services.payment_interface import PaymentRequest, PaymentResponse, PaymentStatus
        
        # Create registry
        registry = PaymentServiceRegistry()
        
        # Create mock provider
        mock_provider = Mock(spec=PaymentServiceInterface)
        mock_provider.provider_name = "test_provider"
        mock_provider.supported_currencies = ["KES", "USD"]
        mock_provider.supported_countries = ["KE", "US"]
        
        # Register provider
        registry.register_provider(mock_provider, is_default=True)
        
        # Test registry functionality
        assert "test_provider" in registry.list_providers()
        assert registry.get_provider("test_provider") == mock_provider
        assert "KES" in registry.get_supported_currencies()
        assert "KE" in registry.get_supported_countries()
        
        print("✅ Payment service registry test passed")
        return True
        
    except Exception as e:
        print(f"❌ Payment service registry test failed: {e}")
        return False

def test_mpesa_service_creation():
    """Test M-Pesa service creation."""
    try:
        from services.mpesa_service import MPesaSTKPushService, MPesaConfig
        
        # Create config
        config = MPesaConfig(
            consumer_key="test_key",
            consumer_secret="test_secret",
            business_short_code="123456",
            lipa_na_mpesa_passkey="test_passkey",
            environment="sandbox",
            callback_url="https://test.com/callback",
            timeout_url="https://test.com/timeout"
        )
        
        # Create service
        service = MPesaSTKPushService(config)
        
        # Check basic properties
        assert service.provider_name == "mpesa"
        assert "KES" in service.supported_currencies
        assert "KE" in service.supported_countries
        
        print("✅ M-Pesa service creation test passed")
        return True
        
    except Exception as e:
        print(f"❌ M-Pesa service creation test failed: {e}")
        return False

async def test_integration_system_status():
    """Test integration system status check."""
    try:
        from integration import IntegrationManager
        
        # Create manager with mocked dependencies
        manager = IntegrationManager()
        
        # Mock the database manager
        manager.db_manager = Mock()
        manager.db_manager.client.table.return_value.select.return_value.limit.return_value.execute = AsyncMock()
        
        # Mock payment registry
        manager.payment_registry = Mock()
        manager.payment_registry.list_providers.return_value = ["mpesa"]
        
        # Mock notification service
        manager.notification_service = Mock()
        manager.notification_service.templates = {"test": "template"}
        
        # Test system status
        status = await manager.get_system_status()
        
        # Verify status structure
        assert "integration_initialized" in status
        assert "database_connected" in status
        assert "payment_providers" in status
        assert "celery_workers" in status
        assert "notification_system" in status
        
        print("✅ Integration system status test passed")
        return True
        
    except Exception as e:
        print(f"❌ Integration system status test failed: {e}")
        return False

def test_backend_client_creation():
    """Test backend client creation."""
    try:
        # Mock config
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))
        
        # Create a mock config
        class MockConfig:
            backend_api_url = "http://localhost:8000"
            backend_api_key = "test_key"
        
        # Mock the config module
        sys.modules['config'] = Mock()
        sys.modules['config'].config = MockConfig()
        
        from bot.utils.backend_client import BackendClient
        
        # Create client
        client = BackendClient()
        
        # Check basic attributes
        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "test_key"
        assert client.timeout == 30.0
        
        print("✅ Backend client creation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Backend client creation test failed: {e}")
        return False

async def run_all_tests():
    """Run all integration tests."""
    print("🚀 Running MyPoolr Circles Integration Tests\n")
    
    tests = [
        ("Integration Manager Creation", test_integration_manager_creation),
        ("Payment Service Registry", test_payment_service_registry),
        ("M-Pesa Service Creation", test_mpesa_service_creation),
        ("Integration System Status", test_integration_system_status),
        ("Backend Client Creation", test_backend_client_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
        
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("⚠️  Some integration tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)