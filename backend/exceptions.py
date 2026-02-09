"""Custom exceptions and error handling for MyPoolr Circles."""

import logging
import traceback
from typing import Any, Dict, Optional, Union
from datetime import datetime
from enum import Enum
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels for classification and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for better classification and handling."""
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    SECURITY = "security"
    SYSTEM = "system"
    CONCURRENCY = "concurrency"
    DATA_CONSISTENCY = "data_consistency"


class ErrorContext(BaseModel):
    """Context information for error tracking and debugging."""
    user_id: Optional[str] = None
    mypoolr_id: Optional[str] = None
    member_id: Optional[str] = None
    transaction_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    additional_data: Dict[str, Any] = {}


class MyPoolrException(Exception):
    """Base exception class for MyPoolr Circles application."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or ErrorContext()
        self.cause = cause
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging and API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context.dict() if self.context else None,
            "cause": str(self.cause) if self.cause else None
        }


class ValidationError(MyPoolrException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs
        )
        self.field = field


class BusinessLogicError(MyPoolrException):
    """Raised when business rules are violated."""
    
    def __init__(self, message: str, rule: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.rule = rule


class DatabaseError(MyPoolrException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.operation = operation


class SecurityError(MyPoolrException):
    """Raised when security violations occur."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="SECURITY_ERROR",
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )


class ConcurrencyError(MyPoolrException):
    """Raised when concurrent operations conflict."""
    
    def __init__(self, message: str, resource: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONCURRENCY_ERROR",
            category=ErrorCategory.CONCURRENCY,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        self.resource = resource


class DataConsistencyError(MyPoolrException):
    """Raised when data consistency issues are detected."""
    
    def __init__(self, message: str, entity: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="DATA_CONSISTENCY_ERROR",
            category=ErrorCategory.DATA_CONSISTENCY,
            severity=ErrorSeverity.CRITICAL,
            recoverable=False,
            **kwargs
        )
        self.entity = entity


class ExternalServiceError(MyPoolrException):
    """Raised when external service calls fail."""
    
    def __init__(self, message: str, service: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.service = service


class SystemError(MyPoolrException):
    """Raised when system-level errors occur."""
    
    def __init__(self, message: str, component: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="SYSTEM_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )
        self.component = component


# Specific business logic exceptions
class InsufficientSecurityDepositError(BusinessLogicError):
    """Raised when security deposit is insufficient."""
    
    def __init__(self, required: float, provided: float, **kwargs):
        super().__init__(
            message=f"Insufficient security deposit. Required: {required}, Provided: {provided}",
            rule="security_deposit_sufficiency",
            **kwargs
        )
        self.required = required
        self.provided = provided


class MemberCapacityExceededError(BusinessLogicError):
    """Raised when member capacity is exceeded."""
    
    def __init__(self, current: int, limit: int, **kwargs):
        super().__init__(
            message=f"Member capacity exceeded. Current: {current}, Limit: {limit}",
            rule="member_capacity_limit",
            **kwargs
        )
        self.current = current
        self.limit = limit


class TierLimitExceededError(BusinessLogicError):
    """Raised when tier limits are exceeded."""
    
    def __init__(self, tier: str, limit_type: str, current: int, limit: int, **kwargs):
        super().__init__(
            message=f"Tier {tier} {limit_type} limit exceeded. Current: {current}, Limit: {limit}",
            rule="tier_limits",
            **kwargs
        )
        self.tier = tier
        self.limit_type = limit_type
        self.current = current
        self.limit = limit


class RotationLockViolationError(SecurityError):
    """Raised when locked members attempt restricted actions."""
    
    def __init__(self, member_id: str, action: str, **kwargs):
        super().__init__(
            message=f"Member {member_id} is locked and cannot perform action: {action}",
            **kwargs
        )
        self.member_id = member_id
        self.action = action


class DuplicateConfirmationError(BusinessLogicError):
    """Raised when duplicate confirmations are attempted."""
    
    def __init__(self, transaction_id: str, confirmation_type: str, **kwargs):
        super().__init__(
            message=f"Transaction {transaction_id} already confirmed by {confirmation_type}",
            rule="unique_confirmation",
            **kwargs
        )
        self.transaction_id = transaction_id
        self.confirmation_type = confirmation_type


def create_error_context(
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    mypoolr_id: Optional[str] = None,
    member_id: Optional[str] = None,
    transaction_id: Optional[str] = None,
    **additional_data
) -> ErrorContext:
    """Create error context from request and additional data."""
    context = ErrorContext(
        user_id=user_id,
        mypoolr_id=mypoolr_id,
        member_id=member_id,
        transaction_id=transaction_id,
        additional_data=additional_data
    )
    
    if request:
        context.endpoint = str(request.url.path)
        context.method = request.method
        context.request_id = request.headers.get("X-Request-ID")
    
    return context