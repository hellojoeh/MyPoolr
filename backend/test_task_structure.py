#!/usr/bin/env python3
"""Test script to validate background task system structure and imports."""

import sys
import logging
import importlib
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all task modules can be imported successfully."""
    modules_to_test = [
        'celery_app',
        'monitoring',
        'scheduler',
        'tasks.reminders',
        'tasks.defaults',
        'tasks.rotation',
        'worker'
    ]
    
    results = {}
    
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            results[module_name] = True
            logger.info(f"✅ Successfully imported {module_name}")
        except Exception as e:
            results[module_name] = False
            logger.error(f"❌ Failed to import {module_name}: {e}")
    
    return results


def test_celery_app_structure():
    """Test Celery app configuration structure."""
    try:
        from celery_app import celery_app
        
        # Check basic configuration
        config_checks = {
            'broker_url': hasattr(celery_app.conf, 'broker_url'),
            'result_backend': hasattr(celery_app.conf, 'result_backend'),
            'task_routes': hasattr(celery_app.conf, 'task_routes'),
            'task_serializer': celery_app.conf.task_serializer == 'json',
            'timezone': celery_app.conf.timezone == 'UTC',
        }
        
        all_passed = all(config_checks.values())
        
        if all_passed:
            logger.info("✅ Celery app configuration structure is correct")
        else:
            logger.error(f"❌ Celery app configuration issues: {config_checks}")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"❌ Celery app structure test failed: {e}")
        return False


def test_task_definitions():
    """Test that task functions are properly defined."""
    task_definitions = {}
    
    # Test reminder tasks
    try:
        from tasks.reminders import (
            process_rotation_reminder,
            schedule_contribution_reminder,
            send_recipient_notification,
            check_contribution_timeout
        )
        task_definitions['reminders'] = True
        logger.info("✅ Reminder tasks properly defined")
    except Exception as e:
        task_definitions['reminders'] = False
        logger.error(f"❌ Reminder tasks definition error: {e}")
    
    # Test default handling tasks
    try:
        from tasks.defaults import (
            handle_contribution_default,
            use_security_deposit_for_contribution,
            apply_default_consequences,
            monitor_default_deadlines
        )
        task_definitions['defaults'] = True
        logger.info("✅ Default handling tasks properly defined")
    except Exception as e:
        task_definitions['defaults'] = False
        logger.error(f"❌ Default handling tasks definition error: {e}")
    
    # Test rotation tasks
    try:
        from tasks.rotation import advance_rotation_schedule
        task_definitions['rotation'] = True
        logger.info("✅ Rotation tasks properly defined")
    except Exception as e:
        task_definitions['rotation'] = False
        logger.error(f"❌ Rotation tasks definition error: {e}")
    
    # Test monitoring tasks
    try:
        from monitoring import (
            TaskMonitor,
            task_monitor,
            monitor_task_execution,
            generate_health_report
        )
        task_definitions['monitoring'] = True
        logger.info("✅ Monitoring tasks properly defined")
    except Exception as e:
        task_definitions['monitoring'] = False
        logger.error(f"❌ Monitoring tasks definition error: {e}")
    
    # Test scheduler tasks
    try:
        from scheduler import (
            TaskScheduler,
            task_scheduler,
            schedule_reminders_daily,
            perform_system_maintenance
        )
        task_definitions['scheduler'] = True
        logger.info("✅ Scheduler tasks properly defined")
    except Exception as e:
        task_definitions['scheduler'] = False
        logger.error(f"❌ Scheduler tasks definition error: {e}")
    
    return task_definitions


def test_worker_manager():
    """Test worker management functionality."""
    try:
        from worker import WorkerManager
        
        # Test initialization
        manager = WorkerManager()
        
        # Check required methods
        required_methods = [
            'start_worker',
            'stop_worker',
            'restart_worker',
            'check_worker_health',
            'monitor_workers',
            'start_all_workers',
            'shutdown',
            'get_worker_stats'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(manager, method):
                missing_methods.append(method)
        
        if not missing_methods:
            logger.info("✅ Worker manager properly structured")
            return True
        else:
            logger.error(f"❌ Worker manager missing methods: {missing_methods}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Worker manager test failed: {e}")
        return False


def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        'celery_app.py',
        'monitoring.py',
        'scheduler.py',
        'worker.py',
        'tasks/__init__.py',
        'tasks/reminders.py',
        'tasks/defaults.py',
        'tasks/rotation.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if not missing_files:
        logger.info("✅ All required files exist")
        return True
    else:
        logger.error(f"❌ Missing files: {missing_files}")
        return False


def test_task_decorators():
    """Test that tasks have proper decorators and configuration."""
    try:
        from tasks.reminders import process_rotation_reminder
        from tasks.defaults import handle_contribution_default
        from monitoring import generate_health_report
        
        # Check if tasks are properly decorated
        tasks_to_check = [
            process_rotation_reminder,
            handle_contribution_default,
            generate_health_report
        ]
        
        properly_decorated = 0
        
        for task in tasks_to_check:
            # Check if it's a Celery task (has task attributes)
            if hasattr(task, 'delay') and hasattr(task, 'apply_async'):
                properly_decorated += 1
                logger.info(f"✅ Task {task.__name__} properly decorated")
            else:
                logger.error(f"❌ Task {task.__name__} not properly decorated")
        
        if properly_decorated == len(tasks_to_check):
            logger.info("✅ All tasks properly decorated")
            return True
        else:
            logger.error(f"❌ {len(tasks_to_check) - properly_decorated} tasks not properly decorated")
            return False
        
    except Exception as e:
        logger.error(f"❌ Task decorator test failed: {e}")
        return False


def run_structure_tests():
    """Run all structure validation tests."""
    logger.info("🚀 Starting background task system structure tests...")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("Celery App Structure", test_celery_app_structure),
        ("Task Definitions", test_task_definitions),
        ("Worker Manager", test_worker_manager),
        ("Task Decorators", test_task_decorators),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = test_func()
            if isinstance(result, dict):
                # For tests that return detailed results
                results[test_name] = all(result.values())
                for sub_test, sub_result in result.items():
                    status = "✅ PASS" if sub_result else "❌ FAIL"
                    logger.info(f"  {sub_test}: {status}")
            else:
                results[test_name] = result
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("STRUCTURE TEST SUMMARY")
    logger.info("="*50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All structure tests passed! Background task system is properly implemented.")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = run_structure_tests()
    sys.exit(0 if success else 1)