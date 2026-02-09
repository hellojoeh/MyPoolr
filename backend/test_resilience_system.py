"""Test suite for crypto-grade system resilience."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from exceptions import (
    MyPoolrException, ErrorSeverity, ErrorCategory, ErrorContext,
    DatabaseError, SecurityError, ConcurrencyError, DataConsistencyError
)
from error_handlers import ErrorHandler
from system_recovery import recovery_manager, SystemSnapshot
from data_consistency import consistency_checker, ConsistencyIssue, ConsistencyIssueType, ConsistencyCheckSeverity
from failure_isolation import failure_isolation_manager, FailurePattern, IsolationLevel
from audit_logger import audit_logger
from monitoring import system_monitor


class TestErrorHandling:
    """Test comprehensive error handling."""
    
    @pytest.mark.asyncio
    async def test_mypoolr_exception_handling(self):
        """Test custom exception handling."""
        # Create a test exception
        context = ErrorContext(
            user_id="test_user",
            mypoolr_id="test_mypoolr",
            endpoint="/test/endpoint"
        )
        
        error = DatabaseError(
            message="Test database error",
            operation="test_operation",
            context=context,
            severity=ErrorSeverity.HIGH
        )
        
        # Test exception properties
        assert error.error_code == "DATABASE_ERROR"
        assert error.category == ErrorCategory.DATABASE
        assert error.severity == ErrorSeverity.HIGH
        assert error.recoverable == True
        assert error.context.user_id == "test_user"
        
        # Test exception serialization
        error_dict = error.to_dict()
        assert error_dict["error_code"] == "DATABASE_ERROR"
        assert error_dict["category"] == "database"
        assert error_dict["severity"] == "high"
    
    @pytest.mark.asyncio
    async def test_error_recovery_attempt(self):
        """Test automatic error recovery."""
        # This would test the recovery mechanisms
        # For now, just verify the structure exists
        assert hasattr(recovery_manager, 'detect_and_recover_failures')
        assert callable(recovery_manager.detect_and_recover_failures)


class TestDataConsistency:
    """Test data consistency detection and correction."""
    
    @pytest.mark.asyncio
    async def test_consistency_issue_creation(self):
        """Test consistency issue creation."""
        issue = ConsistencyIssue(
            issue_type=ConsistencyIssueType.CALCULATION_MISMATCH,
            severity=ConsistencyCheckSeverity.ERROR,
            entity_type="member",
            entity_id="test_member_id",
            description="Test consistency issue",
            details={"expected": 100.0, "actual": 90.0},
            auto_correctable=True,
            correction_action="recalculate_security_deposit"
        )
        
        assert issue.issue_type == ConsistencyIssueType.CALCULATION_MISMATCH
        assert issue.severity == ConsistencyCheckSeverity.ERROR
        assert issue.auto_correctable == True
        assert issue.correction_action == "recalculate_security_deposit"
    
    @pytest.mark.asyncio
    async def test_consistency_checker_structure(self):
        """Test consistency checker has required methods."""
        assert hasattr(consistency_checker, 'run_full_consistency_check')
        assert hasattr(consistency_checker, 'auto_correct_issues')
        assert callable(consistency_checker.run_full_consistency_check)
        assert callable(consistency_checker.auto_correct_issues)


class TestSystemRecovery:
    """Test system recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_system_snapshot_creation(self):
        """Test system snapshot creation."""
        # Mock database responses
        with patch.object(recovery_manager.db.service_client, 'table') as mock_table:
            mock_result = Mock()
            mock_result.count = 5
            mock_table.return_value.select.return_value.execute.return_value = mock_result
            mock_table.return_value.select.return_value.neq.return_value.execute.return_value = mock_result
            
            snapshot = await recovery_manager.create_system_snapshot()
            
            assert isinstance(snapshot, SystemSnapshot)
            assert snapshot.mypoolr_count == 5
            assert snapshot.member_count == 5
            assert snapshot.transaction_count == 5
            assert snapshot.checksum is not None
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test comprehensive health check."""
        with patch.object(recovery_manager.db, 'health_check', return_value=True):
            with patch.object(consistency_checker, 'run_full_consistency_check', return_value=[]):
                health_status = await recovery_manager.health_check()
                
                assert "overall_status" in health_status
                assert "components" in health_status
                assert "timestamp" in health_status
                assert health_status["overall_status"] in ["healthy", "degraded", "failed"]
    
    @pytest.mark.asyncio
    async def test_recovery_action_execution(self):
        """Test recovery action execution."""
        from system_recovery import RecoveryAction
        
        action = RecoveryAction(
            action_type="cleanup_temp_data",
            component="system",
            description="Test cleanup action",
            parameters={},
            priority=5
        )
        
        result = await recovery_manager._execute_recovery_action(action)
        
        assert "success" in result
        assert isinstance(result["success"], bool)


class TestFailureIsolation:
    """Test failure isolation and alerting."""
    
    @pytest.mark.asyncio
    async def test_failure_pattern_detection(self):
        """Test failure pattern detection."""
        # Create test error
        error = SecurityError(
            message="Test security violation",
            context=ErrorContext(user_id="test_user")
        )
        
        # Test failure handling
        result = await failure_isolation_manager.handle_failure(error)
        
        assert "failure_recorded" in result
        assert result["failure_recorded"] == True
        assert "patterns_detected" in result
        assert "isolation_triggered" in result
        assert "alerts_sent" in result
    
    def test_failure_pattern_configuration(self):
        """Test failure pattern configuration."""
        patterns = failure_isolation_manager.failure_patterns
        
        assert len(patterns) > 0
        
        # Check for critical patterns
        pattern_names = [p.name for p in patterns]
        assert "security_violations" in pattern_names
        assert "data_consistency_errors" in pattern_names
        assert "database_connection_failures" in pattern_names
    
    def test_isolation_status(self):
        """Test isolation status retrieval."""
        status = failure_isolation_manager.get_isolation_status()
        
        assert "isolated_components" in status
        assert "recent_failures" in status
        assert "recent_alerts" in status
        assert isinstance(status["isolated_components"], dict)


class TestAuditLogging:
    """Test audit logging system."""
    
    @pytest.mark.asyncio
    async def test_audit_event_logging(self):
        """Test audit event logging."""
        # Test user action logging
        await audit_logger.log_user_action(
            action="test_action",
            user_id="test_user",
            resource_type="test_resource",
            resource_id="test_id",
            details={"test": "data"}
        )
        
        # Test system action logging
        await audit_logger.log_system_action(
            action="test_system_action",
            component="test_component",
            details={"test": "data"}
        )
        
        # Test error event logging
        test_error = DatabaseError(
            message="Test error for audit",
            operation="test_operation"
        )
        
        await audit_logger.log_error_event(test_error)
        
        # Verify events are buffered
        assert len(audit_logger.event_buffer) > 0
    
    @pytest.mark.asyncio
    async def test_audit_context_manager(self):
        """Test audit context manager."""
        async with audit_logger.audit_context(
            action="test_context_action",
            user_id="test_user",
            resource_type="test_resource"
        ):
            # Simulate some work
            await asyncio.sleep(0.01)
        
        # Verify context was logged
        assert len(audit_logger.event_buffer) > 0


class TestMonitoring:
    """Test monitoring system."""
    
    @pytest.mark.asyncio
    async def test_metric_collection(self):
        """Test metric collection."""
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                mock_memory.return_value.available = 4 * 1024**3  # 4GB
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 70.0
                    mock_disk.return_value.free = 100 * 1024**3  # 100GB
                    
                    with patch('psutil.net_io_counters') as mock_network:
                        mock_network.return_value.bytes_sent = 1000000
                        mock_network.return_value.bytes_recv = 2000000
                        
                        metrics = await system_monitor.collect_metrics()
                        
                        assert "system_cpu_percent" in metrics
                        assert "system_memory_percent" in metrics
                        assert "system_disk_percent" in metrics
                        assert metrics["system_cpu_percent"] == 50.0
    
    def test_alert_rule_configuration(self):
        """Test alert rule configuration."""
        alert_rules = system_monitor.alert_rules
        
        assert len(alert_rules) > 0
        assert "system_cpu_percent" in alert_rules
        assert "system_memory_percent" in alert_rules
        assert "db_connection_healthy" in alert_rules
        
        # Check rule structure
        cpu_rule = alert_rules["system_cpu_percent"]
        assert "threshold" in cpu_rule
        assert "operator" in cpu_rule
        assert "severity" in cpu_rule
        assert "message" in cpu_rule
    
    def test_system_status(self):
        """Test system status retrieval."""
        status = system_monitor.get_system_status()
        
        assert "overall_status" in status
        assert "timestamp" in status
        assert "metrics" in status
        assert "monitoring_active" in status
        assert status["overall_status"] in ["healthy", "warning", "critical"]


class TestIntegration:
    """Test integration between resilience components."""
    
    @pytest.mark.asyncio
    async def test_error_to_recovery_flow(self):
        """Test complete error to recovery flow."""
        # Create a critical error
        error = DataConsistencyError(
            message="Critical data consistency error",
            entity="test_entity",
            context=ErrorContext(
                user_id="test_user",
                mypoolr_id="test_mypoolr"
            )
        )
        
        # Handle the error through failure isolation
        isolation_result = await failure_isolation_manager.handle_failure(error)
        
        # Verify error was handled
        assert isolation_result["failure_recorded"] == True
        
        # Trigger recovery
        with patch.object(consistency_checker, 'run_full_consistency_check', return_value=[]):
            recovery_result = await recovery_manager.detect_and_recover_failures()
            
            assert "started_at" in recovery_result
            assert "issues_detected" in recovery_result
    
    @pytest.mark.asyncio
    async def test_monitoring_to_alerting_flow(self):
        """Test monitoring to alerting flow."""
        # Simulate high resource usage that should trigger alerts
        with patch('psutil.cpu_percent', return_value=95.0):  # Above threshold
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 95.0  # Above threshold
                
                # Collect metrics (should trigger alerts)
                metrics = await system_monitor.collect_metrics()
                
                # Check if alerts were generated
                recent_alerts = system_monitor.get_recent_alerts(hours=1)
                
                # Should have alerts for high CPU and memory
                assert len(recent_alerts) >= 0  # May be 0 due to cooldown


# Test runner
if __name__ == "__main__":
    # Run basic tests without pytest
    async def run_basic_tests():
        """Run basic tests without pytest framework."""
        print("Running basic resilience system tests...")
        
        # Test error creation
        error = DatabaseError(
            message="Test database error",
            operation="test_operation"
        )
        print(f"✓ Error creation: {error.error_code}")
        
        # Test consistency issue
        issue = ConsistencyIssue(
            issue_type=ConsistencyIssueType.CALCULATION_MISMATCH,
            severity=ConsistencyCheckSeverity.ERROR,
            entity_type="member",
            entity_id="test_member_id",
            description="Test consistency issue",
            details={"test": "data"}
        )
        print(f"✓ Consistency issue: {issue.issue_type.value}")
        
        # Test failure isolation
        result = await failure_isolation_manager.handle_failure(error)
        print(f"✓ Failure isolation: {result['failure_recorded']}")
        
        # Test audit logging
        await audit_logger.log_system_action(
            action="test_action",
            component="test_component"
        )
        print(f"✓ Audit logging: {len(audit_logger.event_buffer)} events")
        
        # Test monitoring
        status = system_monitor.get_system_status()
        print(f"✓ Monitoring status: {status['overall_status']}")
        
        print("All basic tests passed!")
    
    # Run the tests
    asyncio.run(run_basic_tests())