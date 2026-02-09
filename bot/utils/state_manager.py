"""State management system for conversation flows."""

import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import redis
from loguru import logger

from config import config


class ConversationState(Enum):
    """Conversation states for different workflows."""
    IDLE = "idle"
    CREATING_MYPOOLR = "creating_mypoolr"
    JOINING_MYPOOLR = "joining_mypoolr"
    CONFIRMING_CONTRIBUTION = "confirming_contribution"
    UPGRADING_TIER = "upgrading_tier"
    MANAGING_MEMBERS = "managing_members"


@dataclass
class UserState:
    """User state data structure."""
    user_id: int
    conversation_state: ConversationState = ConversationState.IDLE
    current_step: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def update(self, **kwargs) -> None:
        """Update state data."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.data[key] = value
        self.updated_at = time.time()


class StateManager:
    """Manages user conversation states with Redis persistence."""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(config.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for state management")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory storage.")
            self.redis_client = None
        
        # Fallback in-memory storage
        self._memory_storage: Dict[int, UserState] = {}
        self.state_ttl = 3600  # 1 hour TTL for states
    
    def _get_key(self, user_id: int) -> str:
        """Generate Redis key for user state."""
        return f"mypoolr:state:{user_id}"
    
    def get_state(self, user_id: int) -> UserState:
        """Get user state from storage."""
        if self.redis_client:
            try:
                data = self.redis_client.get(self._get_key(user_id))
                if data:
                    state_dict = json.loads(data)
                    state_dict['conversation_state'] = ConversationState(state_dict['conversation_state'])
                    return UserState(**state_dict)
            except Exception as e:
                logger.error(f"Error getting state from Redis: {e}")
        
        # Fallback to memory storage
        return self._memory_storage.get(user_id, UserState(user_id=user_id))
    
    def set_state(self, state: UserState) -> None:
        """Save user state to storage."""
        state.updated_at = time.time()
        
        if self.redis_client:
            try:
                state_dict = asdict(state)
                state_dict['conversation_state'] = state.conversation_state.value
                
                self.redis_client.setex(
                    self._get_key(state.user_id),
                    self.state_ttl,
                    json.dumps(state_dict)
                )
                return
            except Exception as e:
                logger.error(f"Error saving state to Redis: {e}")
        
        # Fallback to memory storage
        self._memory_storage[state.user_id] = state
    
    def clear_state(self, user_id: int) -> None:
        """Clear user state."""
        if self.redis_client:
            try:
                self.redis_client.delete(self._get_key(user_id))
                return
            except Exception as e:
                logger.error(f"Error clearing state from Redis: {e}")
        
        # Fallback to memory storage
        self._memory_storage.pop(user_id, None)
    
    def start_conversation(self, user_id: int, conversation_type: ConversationState) -> UserState:
        """Start a new conversation flow."""
        state = UserState(
            user_id=user_id,
            conversation_state=conversation_type,
            current_step=0
        )
        self.set_state(state)
        logger.info(f"Started {conversation_type.value} conversation for user {user_id}")
        return state
    
    def advance_step(self, user_id: int, step_data: Optional[Dict[str, Any]] = None) -> UserState:
        """Advance to the next step in conversation."""
        state = self.get_state(user_id)
        state.current_step += 1
        
        if step_data:
            state.data.update(step_data)
        
        self.set_state(state)
        return state
    
    def update_data(self, user_id: int, data: Dict[str, Any]) -> UserState:
        """Update conversation data without advancing step."""
        state = self.get_state(user_id)
        state.data.update(data)
        self.set_state(state)
        return state
    
    def end_conversation(self, user_id: int) -> None:
        """End current conversation and reset to idle."""
        state = self.get_state(user_id)
        state.conversation_state = ConversationState.IDLE
        state.current_step = 0
        state.data.clear()
        self.set_state(state)
        logger.info(f"Ended conversation for user {user_id}")
    
    def is_in_conversation(self, user_id: int) -> bool:
        """Check if user is in an active conversation."""
        state = self.get_state(user_id)
        return state.conversation_state != ConversationState.IDLE
    
    def get_conversation_progress(self, user_id: int) -> Dict[str, Any]:
        """Get conversation progress information."""
        state = self.get_state(user_id)
        
        # Define step counts for each conversation type
        step_counts = {
            ConversationState.CREATING_MYPOOLR: 5,  # Name, Amount, Frequency, Members, Confirm
            ConversationState.JOINING_MYPOOLR: 3,   # Details, Security Deposit, Confirm
            ConversationState.CONFIRMING_CONTRIBUTION: 2,  # Amount, Confirm
            ConversationState.UPGRADING_TIER: 3,    # Select Tier, Payment, Confirm
            ConversationState.MANAGING_MEMBERS: 2,  # Select Action, Execute
        }
        
        total_steps = step_counts.get(state.conversation_state, 1)
        progress_percentage = min((state.current_step / total_steps) * 100, 100)
        
        return {
            "current_step": state.current_step,
            "total_steps": total_steps,
            "progress_percentage": progress_percentage,
            "conversation_type": state.conversation_state.value
        }
    
    def cleanup_expired_states(self) -> int:
        """Clean up expired states (for memory storage)."""
        if self.redis_client:
            return 0  # Redis handles TTL automatically
        
        current_time = time.time()
        expired_users = []
        
        for user_id, state in self._memory_storage.items():
            if current_time - state.updated_at > self.state_ttl:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self._memory_storage[user_id]
        
        logger.info(f"Cleaned up {len(expired_users)} expired states")
        return len(expired_users)