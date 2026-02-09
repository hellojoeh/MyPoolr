"""Abstract payment service interface for modular payment processing."""

from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    MPESA = "mpesa"
    FLUTTERWAVE = "flutterwave"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"


class PaymentRequest(BaseModel):
    """Payment request model."""
    
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="KES", description="Currency code")
    phone_number: str = Field(..., description="Customer phone number")
    reference: str = Field(..., description="Unique payment reference")
    description: str = Field(..., description="Payment description")
    callback_url: Optional[str] = Field(None, description="Payment callback URL")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PaymentResponse(BaseModel):
    """Payment response model."""
    
    payment_id: str = Field(..., description="Payment provider's transaction ID")
    status: PaymentStatus = Field(..., description="Payment status")
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    reference: str = Field(..., description="Payment reference")
    provider_reference: Optional[str] = Field(None, description="Provider's internal reference")
    checkout_url: Optional[str] = Field(None, description="Payment checkout URL if applicable")
    expires_at: Optional[datetime] = Field(None, description="Payment expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CallbackData(BaseModel):
    """Payment callback data model."""
    
    payment_id: str = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Payment status")
    amount: Optional[Decimal] = Field(None, description="Payment amount")
    currency: Optional[str] = Field(None, description="Currency code")
    reference: Optional[str] = Field(None, description="Payment reference")
    provider_reference: Optional[str] = Field(None, description="Provider's reference")
    transaction_date: Optional[datetime] = Field(None, description="Transaction completion date")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw callback data")


class CallbackResponse(BaseModel):
    """Payment callback response model."""
    
    success: bool = Field(..., description="Whether callback was processed successfully")
    payment_id: str = Field(..., description="Payment ID")
    status: PaymentStatus = Field(..., description="Updated payment status")
    message: str = Field(default="", description="Response message")


class PaymentServiceError(Exception):
    """Base exception for payment service errors."""
    
    def __init__(self, message: str, error_code: str = None, provider_error: Any = None):
        self.message = message
        self.error_code = error_code
        self.provider_error = provider_error
        super().__init__(self.message)


class PaymentServiceInterface(ABC):
    """Abstract interface for payment service providers."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the payment provider name."""
        pass
    
    @property
    @abstractmethod
    def supported_currencies(self) -> List[str]:
        """Get list of supported currencies."""
        pass
    
    @property
    @abstractmethod
    def supported_countries(self) -> List[str]:
        """Get list of supported countries."""
        pass
    
    @abstractmethod
    async def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Initiate a payment with the provider.
        
        Args:
            request: Payment request details
            
        Returns:
            PaymentResponse with payment details
            
        Raises:
            PaymentServiceError: If payment initiation fails
        """
        pass
    
    @abstractmethod
    async def query_payment_status(self, payment_id: str) -> PaymentResponse:
        """
        Query the status of a payment.
        
        Args:
            payment_id: Payment ID to query
            
        Returns:
            PaymentResponse with current payment status
            
        Raises:
            PaymentServiceError: If status query fails
        """
        pass
    
    @abstractmethod
    async def handle_callback(self, callback_data: Dict[str, Any]) -> CallbackResponse:
        """
        Handle payment callback from provider.
        
        Args:
            callback_data: Raw callback data from provider
            
        Returns:
            CallbackResponse with processing result
            
        Raises:
            PaymentServiceError: If callback processing fails
        """
        pass
    
    @abstractmethod
    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Cancel a pending payment.
        
        Args:
            payment_id: Payment ID to cancel
            
        Returns:
            True if cancellation was successful
            
        Raises:
            PaymentServiceError: If cancellation fails
        """
        pass
    
    @abstractmethod
    async def validate_callback_signature(self, callback_data: Dict[str, Any], signature: str) -> bool:
        """
        Validate callback signature for security.
        
        Args:
            callback_data: Raw callback data
            signature: Callback signature to validate
            
        Returns:
            True if signature is valid
        """
        pass
    
    def is_currency_supported(self, currency: str) -> bool:
        """Check if currency is supported by this provider."""
        return currency.upper() in [c.upper() for c in self.supported_currencies]
    
    def is_country_supported(self, country: str) -> bool:
        """Check if country is supported by this provider."""
        return country.upper() in [c.upper() for c in self.supported_countries]


class PaymentServiceRegistry:
    """Registry for managing multiple payment service providers."""
    
    def __init__(self):
        self._providers: Dict[str, PaymentServiceInterface] = {}
        self._default_provider: Optional[str] = None
    
    def register_provider(self, provider: PaymentServiceInterface, is_default: bool = False):
        """Register a payment service provider."""
        self._providers[provider.provider_name] = provider
        
        if is_default or not self._default_provider:
            self._default_provider = provider.provider_name
    
    def get_provider(self, provider_name: str = None) -> PaymentServiceInterface:
        """Get a payment service provider by name."""
        if provider_name is None:
            provider_name = self._default_provider
        
        if provider_name not in self._providers:
            raise PaymentServiceError(f"Payment provider '{provider_name}' not found")
        
        return self._providers[provider_name]
    
    def get_provider_for_currency(self, currency: str) -> PaymentServiceInterface:
        """Get the best provider for a specific currency."""
        for provider in self._providers.values():
            if provider.is_currency_supported(currency):
                return provider
        
        raise PaymentServiceError(f"No provider supports currency '{currency}'")
    
    def get_provider_for_country(self, country: str) -> PaymentServiceInterface:
        """Get the best provider for a specific country."""
        for provider in self._providers.values():
            if provider.is_country_supported(country):
                return provider
        
        raise PaymentServiceError(f"No provider supports country '{country}'")
    
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def get_supported_currencies(self) -> List[str]:
        """Get all currencies supported by any provider."""
        currencies = set()
        for provider in self._providers.values():
            currencies.update(provider.supported_currencies)
        return list(currencies)
    
    def get_supported_countries(self) -> List[str]:
        """Get all countries supported by any provider."""
        countries = set()
        for provider in self._providers.values():
            countries.update(provider.supported_countries)
        return list(countries)