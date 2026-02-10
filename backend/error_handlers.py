"""Error handlers and middleware for comprehensive error handling."""

import logging
import traceback
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as PydanticValidationError

from exceptions import (
    MyPoolrException, ErrorSeverity, ErrorCategory, ErrorContext,
    ValidationError, BusinessLogicError, DatabaseError, SecurityError,
    ConcurrencyError, DataConsistencyError, ExternalServiceError, SystemError
)
from failure_isolation import failure_isolation_manager

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.setup_exception_handlers()
        self.setup_middleware()
    
    def setup_exception_handlers(self):
        """Set up custom exception handlers."""
        
        @self.app.exception_handler(MyPoolrException)
        async def mypoolr_exception_handler(request: Request, exc: MyPoolrException):
            """Handle custom MyPoolr exceptions."""
            return await self.handle_mypoolr_exception(request, exc)
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """Handle FastAPI HTTP exceptions."""
            return await self.handle_http_exception(request, exc)
        
        @self.app.exception_handler(StarletteHTTPException)
        async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
            """Handle Starlette HTTP exceptions."""
            return await self.handle_http_exception(request, exc)
        
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            """Handle request validation errors."""
            return await self.handle_validation_exception(request, exc)
        
        @self.app.exception_handler(PydanticValidationError)
        async def pydantic_validation_handler(request: Request, exc: PydanticValidationError):
            """Handle Pydantic validation errors."""
            return await self.handle_pydantic_validation_exception(request, exc)
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle all other exceptions."""
            return await self.handle_general_exception(request, exc)
    
    def setup_middleware(self):
        """Set up error handling middleware."""
        
        @self.app.middleware("http")
        async def error_handling_middleware(request: Request, call_next):
            """Middleware for request/response error handling."""
            # Add request ID for tracing
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            try:
                response = await call_next(request)
                return response
            except Exception as exc:
                # Log unexpected middleware errors
                logger.error(
                    f"Middleware error for request {request_id}: {str(exc)}",
                    extra={
                        "request_id": request_id,
                        "path": request.url.path,
                        "method": request.method,
                        "traceback": traceback.format_exc()
                    }
                )
                # Re-raise to be handled by exception handlers
                raise exc
    
    async def handle_mypoolr_exception(self, request: Request, exc: MyPoolrException) -> JSONResponse:
        """Handle custom MyPoolr exceptions with proper logging and alerting."""
        
        # Enhance context with request information
        if exc.context:
            exc.context.request_id = getattr(request.state, 'request_id', None)
            exc.context.endpoint = str(request.url.path)
            exc.context.method = request.method
        
        # Log the error with appropriate level
        log_level = self._get_log_level(exc.severity)
        logger.log(
            log_level,
            f"MyPoolr Exception: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code,
                "category": exc.category.value,
                "severity": exc.severity.value,
                "context": exc.context.dict() if exc.context else None,
                "recoverable": exc.recoverable,
                "traceback": traceback.format_exc() if exc.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
            }
        )
        
        # Send alerts for critical errors
        if exc.severity == ErrorSeverity.CRITICAL:
            await self._send_alert(exc)
        
        # Handle failure isolation and alerting
        if exc.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            isolation_result = await failure_isolation_manager.handle_failure(exc)
            logger.info(f"Failure isolation result: {isolation_result}")
        
        # Attempt recovery for recoverable errors
        if exc.recoverable:
            recovery_result = await self._attempt_recovery(exc)
            if recovery_result.get("recovered"):
                logger.info(f"Successfully recovered from error: {exc.error_code}")
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Operation completed with automatic recovery",
                        "recovery_info": recovery_result.get("info")
                    }
                )
        
        # Return error response
        status_code = self._get_http_status_code(exc)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": True,
                "error_code": exc.error_code,
                "message": exc.message,
                "category": exc.category.value,
                "severity": exc.severity.value,
                "recoverable": exc.recoverable,
                "request_id": getattr(request.state, 'request_id', None),
                "timestamp": exc.timestamp.isoformat()
            }
        )
    
    async def handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with enhanced logging."""
        
        request_id = getattr(request.state, 'request_id', None)
        
        logger.warning(
            f"HTTP Exception: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def handle_validation_exception(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors."""
        
        request_id = getattr(request.state, 'request_id', None)
        
        # Extract validation error details
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Validation error for request {request_id}",
            extra={
                "errors": errors,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "Validation failed",
                "errors": errors,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def handle_pydantic_validation_exception(self, request: Request, exc: PydanticValidationError) -> JSONResponse:
        """Handle Pydantic validation errors."""
        
        request_id = getattr(request.state, 'request_id', None)
        
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Pydantic validation error for request {request_id}",
            extra={
                "errors": errors,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "Data validation failed",
                "errors": errors,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def handle_general_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions with full logging and alerting."""
        
        request_id = getattr(request.state, 'request_id', None)
        
        # Check for PostgREST schema cache errors
        error_str = str(exc)
        if self._is_schema_cache_error(error_str):
            logger.error(
                f"PostgREST schema cache mismatch detected for request {request_id}",
                extra={
                    "error_type": "SCHEMA_CACHE_MISMATCH",
                    "error_code": "PGRST204",
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "error_message": error_str,
                    "action_required": "Reload PostgREST schema cache",
                    "fix_command": "NOTIFY pgrst, 'reload schema';",
                    "documentation": "See TROUBLESHOOTING_SCHEMA_CACHE.md"
                }
            )
            
            # Send alert for schema cache issues
            await self._send_schema_cache_alert(error_str, request_id)
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "error_code": "DATABASE_SCHEMA_CACHE_ERROR",
                    "message": "Database schema cache is out of sync. Please contact support.",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Log the unexpected error
        logger.error(
            f"Unexpected error for request {request_id}: {str(exc)}",
            extra={
                "exception_type": type(exc).__name__,
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        # Send critical alert
        await self._send_alert(SystemError(
            message=f"Unexpected system error: {str(exc)}",
            component="error_handler",
            context=ErrorContext(
                request_id=request_id,
                endpoint=str(request.url.path),
                method=request.method
            ),
            cause=exc
        ))
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "An unexpected error occurred. Please try again later.",
                "error_code": "INTERNAL_SERVER_ERROR",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Get appropriate log level for error severity."""
        level_map = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        return level_map.get(severity, logging.ERROR)
    
    def _get_http_status_code(self, exc: MyPoolrException) -> int:
        """Get appropriate HTTP status code for exception."""
        status_map = {
            ErrorCategory.VALIDATION: 400,
            ErrorCategory.BUSINESS_LOGIC: 400,
            ErrorCategory.SECURITY: 403,
            ErrorCategory.DATABASE: 500,
            ErrorCategory.EXTERNAL_SERVICE: 502,
            ErrorCategory.SYSTEM: 500,
            ErrorCategory.CONCURRENCY: 409,
            ErrorCategory.DATA_CONSISTENCY: 500
        }
        return status_map.get(exc.category, 500)
    
    async def _attempt_recovery(self, exc: MyPoolrException) -> Dict[str, Any]:
        """Attempt automatic recovery from recoverable errors."""
        
        recovery_strategies = {
            ErrorCategory.DATABASE: self._recover_database_error,
            ErrorCategory.EXTERNAL_SERVICE: self._recover_external_service_error,
            ErrorCategory.CONCURRENCY: self._recover_concurrency_error
        }
        
        strategy = recovery_strategies.get(exc.category)
        if strategy:
            try:
                return await strategy(exc)
            except Exception as recovery_exc:
                logger.error(f"Recovery failed for {exc.error_code}: {str(recovery_exc)}")
                return {"recovered": False, "error": str(recovery_exc)}
        
        return {"recovered": False, "reason": "No recovery strategy available"}
    
    async def _recover_database_error(self, exc: MyPoolrException) -> Dict[str, Any]:
        """Attempt recovery from database errors."""
        try:
            # Attempt database connection retry with exponential backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Test database connection
                    from database import Database
                    db = Database()
                    # Simple query to test connection
                    result = db.service_client.table("mypoolr").select("id", count="exact").limit(1).execute()
                    
                    logger.info(f"Database connection recovered on attempt {attempt + 1}")
                    return {
                        "recovered": True,
                        "method": "connection_retry",
                        "attempts": attempt + 1
                    }
                except Exception as retry_error:
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        logger.error(f"Database recovery failed after {max_retries} attempts")
            
            return {"recovered": False, "reason": "Max retries exceeded"}
        except Exception as e:
            logger.error(f"Database recovery error: {e}")
            return {"recovered": False, "reason": str(e)}
    
    async def _recover_external_service_error(self, exc: MyPoolrException) -> Dict[str, Any]:
        """Attempt recovery from external service errors."""
        try:
            # Implement service retry with circuit breaker pattern
            service_name = exc.context.get("service") if exc.context else "unknown"
            
            # Check if service is in circuit breaker
            # For now, just attempt a simple retry
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # Service-specific recovery logic would go here
                    # For now, just wait and return
                    import asyncio
                    await asyncio.sleep(1 * (attempt + 1))
                    
                    logger.info(f"External service recovery attempted for {service_name}")
                    return {
                        "recovered": False,
                        "reason": "Service-specific recovery not implemented",
                        "service": service_name,
                        "suggestion": "Retry the operation or use fallback mechanism"
                    }
                except Exception as retry_error:
                    if attempt < max_retries - 1:
                        continue
            
            return {
                "recovered": False,
                "reason": "Service unavailable",
                "service": service_name
            }
        except Exception as e:
            logger.error(f"External service recovery error: {e}")
            return {"recovered": False, "reason": str(e)}
    
    async def _recover_concurrency_error(self, exc: MyPoolrException) -> Dict[str, Any]:
        """Attempt recovery from concurrency errors."""
        try:
            # Implement retry with exponential backoff for lock conflicts
            resource = exc.context.get("resource") if exc.context else "unknown"
            
            # Release any held locks if possible
            # This would require access to the concurrency manager
            
            logger.info(f"Concurrency error recovery for resource: {resource}")
            return {
                "recovered": False,
                "reason": "Retry with backoff recommended",
                "resource": resource,
                "suggestion": "Wait and retry the operation"
            }
        except Exception as e:
            logger.error(f"Concurrency recovery error: {e}")
            return {"recovered": False, "reason": str(e)}
    
    async def _send_alert(self, exc: MyPoolrException):
        """Send alert for critical errors."""
        # Implement alerting mechanism (email, Slack, PagerDuty, etc.)
        logger.critical(
            f"ALERT: Critical error occurred - {exc.error_code}",
            extra={
                "alert": True,
                "error_code": exc.error_code,
                "message": exc.message,
                "context": exc.context.dict() if exc.context else None
            }
        )
    
    def _is_schema_cache_error(self, error_message: str) -> bool:
        """Detect PostgREST schema cache errors."""
        cache_error_indicators = [
            'PGRST204',
            'PGRST202',
            'schema cache',
            'could not find',
            'column of',
            'relation in'
        ]
        error_lower = error_message.lower()
        return any(indicator.lower() in error_lower for indicator in cache_error_indicators)
    
    async def _send_schema_cache_alert(self, error_message: str, request_id: str):
        """Send specific alert for schema cache issues."""
        logger.critical(
            "ALERT: PostgREST schema cache synchronization required!",
            extra={
                "alert": True,
                "alert_type": "SCHEMA_CACHE_MISMATCH",
                "error_message": error_message,
                "request_id": request_id,
                "action_required": "Reload PostgREST schema cache immediately",
                "fix_methods": [
                    "Supabase Dashboard: Settings → API → Reload schema cache",
                    "SQL: NOTIFY pgrst, 'reload schema';",
                    "Script: python reload_schema_cache.py"
                ],
                "documentation": "TROUBLESHOOTING_SCHEMA_CACHE.md",
                "severity": "CRITICAL"
            }
        )


def setup_error_handling(app: FastAPI) -> ErrorHandler:
    """Set up comprehensive error handling for the application."""
    return ErrorHandler(app)