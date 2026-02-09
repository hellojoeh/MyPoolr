"""M-Pesa STK Push payment service implementation."""

import base64
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel

from .payment_interface import (
    PaymentServiceInterface,
    PaymentRequest,
    PaymentResponse,
    CallbackData,
    CallbackResponse,
    PaymentStatus,
    PaymentServiceError
)


class MPesaConfig(BaseModel):
    """M-Pesa configuration model."""
    
    consumer_key: str
    consumer_secret: str
    business_short_code: str
    lipa_na_mpesa_passkey: str
    environment: str = "sandbox"  # sandbox or production
    callback_url: str
    timeout_url: str


class MPesaAuthManager:
    """Handles M-Pesa API authentication."""
    
    def __init__(self, consumer_key: str, consumer_secret: str, environment: str = "sandbox"):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.environment = environment
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    @property
    def auth_url(self) -> str:
        """Get authentication URL based on environment."""
        if self.environment == "production":
            return "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        return "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if self._access_token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._access_token
        
        await self._refresh_access_token()
        return self._access_token
    
    async def _refresh_access_token(self):
        """Refresh the access token from M-Pesa API."""
        try:
            # Create basic auth header
            credentials = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(self.auth_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                self._access_token = data["access_token"]
                expires_in = int(data["expires_in"])
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # 60s buffer
                
        except Exception as e:
            raise PaymentServiceError(f"Failed to get M-Pesa access token: {str(e)}", "AUTH_ERROR")


class MPesaSTKPushService(PaymentServiceInterface):
    """M-Pesa STK Push payment service implementation."""
    
    def __init__(self, config: MPesaConfig):
        self.config = config
        self.auth_manager = MPesaAuthManager(
            config.consumer_key,
            config.consumer_secret,
            config.environment
        )
    
    @property
    def provider_name(self) -> str:
        return "mpesa"
    
    @property
    def supported_currencies(self) -> List[str]:
        return ["KES"]
    
    @property
    def supported_countries(self) -> List[str]:
        return ["KE"]
    
    @property
    def stk_push_url(self) -> str:
        """Get STK Push URL based on environment."""
        if self.config.environment == "production":
            return "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        return "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    @property
    def query_url(self) -> str:
        """Get transaction status query URL."""
        if self.config.environment == "production":
            return "https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query"
        return "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query"
    
    def _generate_password(self, timestamp: str) -> str:
        """Generate M-Pesa API password."""
        data_to_encode = f"{self.config.business_short_code}{self.config.lipa_na_mpesa_passkey}{timestamp}"
        return base64.b64encode(data_to_encode.encode()).decode()
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for M-Pesa (254XXXXXXXXX)."""
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different formats
        if phone.startswith('254'):
            return phone
        elif phone.startswith('0'):
            return f"254{phone[1:]}"
        elif len(phone) == 9:
            return f"254{phone}"
        else:
            raise PaymentServiceError(f"Invalid phone number format: {phone_number}", "INVALID_PHONE")
    
    async def initiate_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Initiate M-Pesa STK Push payment."""
        try:
            # Get access token
            access_token = await self.auth_manager.get_access_token()
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._generate_password(timestamp)
            
            # Format phone number
            phone_number = self._format_phone_number(request.phone_number)
            
            # Prepare STK Push request
            stk_request = {
                "BusinessShortCode": self.config.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(request.amount),  # M-Pesa expects integer
                "PartyA": phone_number,
                "PartyB": self.config.business_short_code,
                "PhoneNumber": phone_number,
                "CallBackURL": self.config.callback_url,
                "AccountReference": request.reference,
                "TransactionDesc": request.description
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Make STK Push request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.stk_push_url,
                    json=stk_request,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise PaymentServiceError(
                        f"M-Pesa STK Push failed: {error_data.get('errorMessage', 'Unknown error')}",
                        error_data.get('errorCode', 'STK_PUSH_ERROR')
                    )
                
                data = response.json()
                
                # Check if request was successful
                if data.get("ResponseCode") != "0":
                    raise PaymentServiceError(
                        f"M-Pesa STK Push failed: {data.get('ResponseDescription', 'Unknown error')}",
                        data.get("ResponseCode", "STK_PUSH_ERROR")
                    )
                
                # Return payment response
                return PaymentResponse(
                    payment_id=data["CheckoutRequestID"],
                    status=PaymentStatus.PENDING,
                    amount=request.amount,
                    currency=request.currency,
                    reference=request.reference,
                    provider_reference=data["MerchantRequestID"],
                    expires_at=datetime.utcnow() + timedelta(minutes=5),  # STK Push expires in 5 minutes
                    metadata={
                        "merchant_request_id": data["MerchantRequestID"],
                        "checkout_request_id": data["CheckoutRequestID"],
                        "phone_number": phone_number,
                        "timestamp": timestamp
                    }
                )
                
        except PaymentServiceError:
            raise
        except Exception as e:
            raise PaymentServiceError(f"Failed to initiate M-Pesa payment: {str(e)}", "INITIATION_ERROR")
    
    async def query_payment_status(self, payment_id: str) -> PaymentResponse:
        """Query M-Pesa payment status."""
        try:
            # Get access token
            access_token = await self.auth_manager.get_access_token()
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._generate_password(timestamp)
            
            # Prepare query request
            query_request = {
                "BusinessShortCode": self.config.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": payment_id
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Make query request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.query_url,
                    json=query_request,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise PaymentServiceError(
                        f"M-Pesa query failed: {error_data.get('errorMessage', 'Unknown error')}",
                        error_data.get('errorCode', 'QUERY_ERROR')
                    )
                
                data = response.json()
                
                # Map M-Pesa result codes to payment status
                result_code = data.get("ResultCode")
                if result_code == "0":
                    status = PaymentStatus.COMPLETED
                elif result_code in ["1032", "1037"]:  # User cancelled or timeout
                    status = PaymentStatus.CANCELLED
                elif result_code == "1":  # Insufficient funds
                    status = PaymentStatus.FAILED
                else:
                    status = PaymentStatus.PENDING
                
                return PaymentResponse(
                    payment_id=payment_id,
                    status=status,
                    amount=Decimal(str(data.get("Amount", 0))),
                    currency="KES",
                    reference=data.get("AccountReference", ""),
                    provider_reference=data.get("MerchantRequestID"),
                    metadata={
                        "result_code": result_code,
                        "result_desc": data.get("ResultDesc", ""),
                        "mpesa_receipt_number": data.get("MpesaReceiptNumber"),
                        "transaction_date": data.get("TransactionDate")
                    }
                )
                
        except PaymentServiceError:
            raise
        except Exception as e:
            raise PaymentServiceError(f"Failed to query M-Pesa payment: {str(e)}", "QUERY_ERROR")
    
    async def handle_callback(self, callback_data: Dict[str, Any]) -> CallbackResponse:
        """Handle M-Pesa callback."""
        try:
            # Extract callback data
            stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
            
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            merchant_request_id = stk_callback.get("MerchantRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            
            if not checkout_request_id:
                raise PaymentServiceError("Missing CheckoutRequestID in callback", "INVALID_CALLBACK")
            
            # Determine payment status
            if result_code == 0:
                status = PaymentStatus.COMPLETED
            elif result_code in [1032, 1037]:  # User cancelled or timeout
                status = PaymentStatus.CANCELLED
            else:
                status = PaymentStatus.FAILED
            
            return CallbackResponse(
                success=True,
                payment_id=checkout_request_id,
                status=status,
                message=result_desc or "Callback processed successfully"
            )
            
        except PaymentServiceError:
            raise
        except Exception as e:
            raise PaymentServiceError(f"Failed to process M-Pesa callback: {str(e)}", "CALLBACK_ERROR")
    
    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel M-Pesa payment (not supported by M-Pesa STK Push)."""
        # M-Pesa STK Push doesn't support cancellation
        # Payments automatically expire after 5 minutes
        return False
    
    async def validate_callback_signature(self, callback_data: Dict[str, Any], signature: str) -> bool:
        """Validate M-Pesa callback signature."""
        # M-Pesa doesn't provide signature validation for STK Push callbacks
        # In production, you should validate the source IP and use HTTPS
        return True