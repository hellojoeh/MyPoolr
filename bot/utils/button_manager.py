"""World-class button management system with state handling."""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import time
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger


class ButtonState(Enum):
    """Button states for visual feedback."""
    NORMAL = "normal"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ButtonConfig:
    """Configuration for a single button."""
    text: str
    callback_data: str
    state: ButtonState = ButtonState.NORMAL
    emoji: Optional[str] = None
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_display_text(self) -> str:
        """Get the display text with state indicators."""
        base_text = f"{self.emoji} {self.text}" if self.emoji else self.text
        
        if self.state == ButtonState.LOADING:
            return f"⏳ {base_text}"
        elif self.state == ButtonState.SUCCESS:
            return f"✅ {base_text}"
        elif self.state == ButtonState.ERROR:
            return f"❌ {base_text}"
        elif self.state == ButtonState.DISABLED:
            return f"🚫 {base_text}"
        
        return base_text


@dataclass
class ButtonGrid:
    """Configuration for a grid of buttons."""
    buttons: List[List[ButtonConfig]]
    max_buttons_per_row: int = 3
    
    def add_row(self, buttons: List[ButtonConfig]) -> None:
        """Add a row of buttons."""
        self.buttons.append(buttons)
    
    def add_button(self, button: ButtonConfig, row_index: int = -1) -> None:
        """Add a button to a specific row (default: last row)."""
        if not self.buttons:
            self.buttons.append([])
        
        target_row = self.buttons[row_index]
        if len(target_row) >= self.max_buttons_per_row:
            # Create new row if current row is full
            self.buttons.append([button])
        else:
            target_row.append(button)


class ButtonManager:
    """World-class button management system with trillion-dollar design."""
    
    def __init__(self):
        self._button_states: Dict[str, ButtonState] = {}
        self._button_callbacks: Dict[str, Callable] = {}
        self._button_metadata: Dict[str, Dict[str, Any]] = {}
        self._button_animations: Dict[str, List[str]] = {}
        self._transition_callbacks: Dict[str, Callable] = {}
    
    def create_button(
        self,
        text: str,
        callback_data: str,
        emoji: Optional[str] = None,
        state: ButtonState = ButtonState.NORMAL,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ButtonConfig:
        """Create a new button configuration."""
        return ButtonConfig(
            text=text,
            callback_data=callback_data,
            emoji=None,  # Remove emojis by default for premium look
            state=state,
            url=url,
            metadata=metadata or {}
        )
    
    def create_grid(self, max_buttons_per_row: int = 3) -> ButtonGrid:
        """Create a new button grid."""
        return ButtonGrid(buttons=[], max_buttons_per_row=max_buttons_per_row)
    
    def build_keyboard(self, grid: ButtonGrid) -> InlineKeyboardMarkup:
        """Build InlineKeyboardMarkup from ButtonGrid."""
        keyboard = []
        
        for row in grid.buttons:
            keyboard_row = []
            for button in row:
                if button.url:
                    # URL button
                    keyboard_row.append(
                        InlineKeyboardButton(
                            text=button.get_display_text(),
                            url=button.url
                        )
                    )
                else:
                    # Callback button
                    keyboard_row.append(
                        InlineKeyboardButton(
                            text=button.get_display_text(),
                            callback_data=button.callback_data
                        )
                    )
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def update_button_state(self, callback_data: str, state: ButtonState) -> None:
        """Update the state of a button."""
        self._button_states[callback_data] = state
        logger.debug(f"Button {callback_data} state updated to {state.value}")
    
    def get_button_state(self, callback_data: str) -> ButtonState:
        """Get the current state of a button."""
        return self._button_states.get(callback_data, ButtonState.NORMAL)
    
    def set_button_metadata(self, callback_data: str, metadata: Dict[str, Any]) -> None:
        """Set metadata for a button."""
        self._button_metadata[callback_data] = metadata
    
    def get_button_metadata(self, callback_data: str) -> Dict[str, Any]:
        """Get metadata for a button."""
        return self._button_metadata.get(callback_data, {})
    
    def register_callback(self, callback_data: str, callback_func: Callable) -> None:
        """Register a callback function for a button."""
        self._button_callbacks[callback_data] = callback_func
    
    def get_callback(self, callback_data: str) -> Optional[Callable]:
        """Get the callback function for a button."""
        return self._button_callbacks.get(callback_data)
    
    # Predefined button templates for common use cases
    
    def create_navigation_buttons(self, back_data: str = "back", home_data: str = "home") -> ButtonGrid:
        """Create standard navigation buttons."""
        grid = self.create_grid()
        grid.add_row([
            self.create_button("Main Menu", home_data),
            self.create_button("Back", back_data)
        ])
        return grid
    
    def create_confirmation_buttons(self, confirm_data: str, cancel_data: str) -> ButtonGrid:
        """Create confirmation buttons."""
        grid = self.create_grid()
        grid.add_row([
            self.create_button("Confirm", confirm_data),
            self.create_button("Cancel", cancel_data)
        ])
        return grid
    
    def create_pagination_buttons(
        self,
        current_page: int,
        total_pages: int,
        base_callback: str
    ) -> ButtonGrid:
        """Create pagination buttons."""
        grid = self.create_grid()
        buttons = []
        
        if current_page > 1:
            buttons.append(
                self.create_button("⬅️ Previous", f"{base_callback}:prev:{current_page-1}")
            )
        
        buttons.append(
            self.create_button(f"{current_page}/{total_pages}", "noop", state=ButtonState.DISABLED)
        )
        
        if current_page < total_pages:
            buttons.append(
                self.create_button("Next ➡️", f"{base_callback}:next:{current_page+1}")
            )
        
        grid.add_row(buttons)
        return grid
    
    def create_country_selection_buttons(self, countries: List[Dict[str, str]]) -> ButtonGrid:
        """Create country selection buttons with flag emojis."""
        grid = self.create_grid(max_buttons_per_row=2)
        
        for country in countries:
            button = self.create_button(
                text=country["name"],
                callback_data=f"country:{country['code']}",
                emoji=country.get("flag", "🏳️")
            )
            grid.add_button(button)
        
        return grid
    
    def create_tier_selection_buttons(self, tiers: List[Dict[str, Any]]) -> ButtonGrid:
        """Create tier selection buttons with feature highlights."""
        grid = self.create_grid(max_buttons_per_row=2)
        
        for tier in tiers:
            emoji = "⭐" * tier.get("stars", 1)
            price_text = f" - ${tier['price']}/mo" if tier.get("price", 0) > 0 else " - Free"
            
            button = self.create_button(
                text=f"{tier['name']}{price_text}",
                callback_data=f"tier:{tier['id']}",
                emoji=emoji
            )
            grid.add_button(button)
        
        return grid
    
    # Advanced button features for trillion-dollar experience
    
    def create_animated_loading_button(self, base_text: str, callback_data: str) -> ButtonConfig:
        """Create a button with loading animation frames."""
        loading_frames = ["⏳", "⌛", "⏳", "⌛"]
        self._button_animations[callback_data] = loading_frames
        
        return self.create_button(
            text=base_text,
            callback_data=callback_data,
            state=ButtonState.NORMAL
        )
    
    async def animate_button_loading(self, callback_data: str, update_func: Callable) -> None:
        """Animate button loading state with smooth transitions."""
        frames = self._button_animations.get(callback_data, ["⏳"])
        
        for frame in frames:
            # Update button with current frame
            await update_func(f"{frame} Processing...")
            await asyncio.sleep(0.5)  # Smooth transition timing
    
    def create_success_feedback_button(self, text: str, callback_data: str) -> ButtonConfig:
        """Create button with success feedback animation."""
        return self.create_button(
            text=text,
            callback_data=callback_data,
            state=ButtonState.SUCCESS
        )
    
    def create_responsive_grid(self, buttons: List[ButtonConfig], screen_size: str = "mobile") -> ButtonGrid:
        """Create responsive button grid based on screen size."""
        if screen_size == "desktop":
            max_per_row = 4
        elif screen_size == "tablet":
            max_per_row = 3
        else:  # mobile
            max_per_row = 2
        
        grid = self.create_grid(max_buttons_per_row=max_per_row)
        
        # Distribute buttons evenly across rows
        for i in range(0, len(buttons), max_per_row):
            row_buttons = buttons[i:i + max_per_row]
            grid.add_row(row_buttons)
        
        return grid
    
    def create_contextual_menu(self, context: str, user_role: str = "member") -> ButtonGrid:
        """Create contextual menu based on user role and current context."""
        grid = self.create_grid()
        
        if context == "mypoolr_main":
            if user_role == "admin":
                grid.add_row([
                    self.create_button("👥 Manage Members", "manage_members", emoji="👥"),
                    self.create_button("📊 View Stats", "view_stats", emoji="📊")
                ])
                grid.add_row([
                    self.create_button("⚙️ Settings", "settings", emoji="⚙️"),
                    self.create_button("🔄 Rotate Now", "force_rotate", emoji="🔄")
                ])
            else:
                grid.add_row([
                    self.create_button("💰 My Contributions", "my_contributions", emoji="💰"),
                    self.create_button("📅 Schedule", "view_schedule", emoji="📅")
                ])
        
        elif context == "contribution_flow":
            grid.add_row([
                self.create_button("✅ Confirm Payment", "confirm_payment", emoji="✅"),
                self.create_button("📸 Upload Receipt", "upload_receipt", emoji="📸")
            ])
            grid.add_row([
                self.create_button("❌ Cancel", "cancel_contribution", emoji="❌")
            ])
        
        # Add universal navigation
        nav_buttons = self.create_navigation_buttons()
        for row in nav_buttons.buttons:
            grid.add_row(row)
        
        return grid
    
    def create_smart_pagination(
        self,
        items: List[Any],
        current_page: int,
        items_per_page: int,
        base_callback: str
    ) -> ButtonGrid:
        """Create smart pagination with jump-to-page options."""
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        grid = self.create_grid()
        
        # Navigation buttons
        nav_buttons = []
        
        if current_page > 1:
            nav_buttons.append(
                self.create_button("⏪ First", f"{base_callback}:page:1")
            )
            nav_buttons.append(
                self.create_button("⬅️ Prev", f"{base_callback}:page:{current_page-1}")
            )
        
        # Current page indicator
        nav_buttons.append(
            self.create_button(
                f"{current_page}/{total_pages}",
                "noop",
                state=ButtonState.DISABLED
            )
        )
        
        if current_page < total_pages:
            nav_buttons.append(
                self.create_button("Next ➡️", f"{base_callback}:page:{current_page+1}")
            )
            nav_buttons.append(
                self.create_button("Last ⏩", f"{base_callback}:page:{total_pages}")
            )
        
        grid.add_row(nav_buttons)
        
        # Quick jump buttons for large datasets
        if total_pages > 10:
            jump_buttons = []
            jump_pages = [1, total_pages // 4, total_pages // 2, 3 * total_pages // 4, total_pages]
            
            for page in jump_pages:
                if page != current_page and 1 <= page <= total_pages:
                    jump_buttons.append(
                        self.create_button(f"→ {page}", f"{base_callback}:page:{page}")
                    )
            
            if jump_buttons:
                grid.add_row(jump_buttons[:3])  # Limit to 3 jump buttons per row
        
        return grid
    
    def register_transition_callback(self, from_state: ButtonState, to_state: ButtonState, callback: Callable) -> None:
        """Register callback for button state transitions."""
        key = f"{from_state.value}:{to_state.value}"
        self._transition_callbacks[key] = callback
    
    async def transition_button_state(self, callback_data: str, new_state: ButtonState) -> None:
        """Transition button state with callback execution."""
        old_state = self.get_button_state(callback_data)
        
        # Execute transition callback if registered
        transition_key = f"{old_state.value}:{new_state.value}"
        if transition_key in self._transition_callbacks:
            await self._transition_callbacks[transition_key](callback_data, old_state, new_state)
        
        # Update state
        self.update_button_state(callback_data, new_state)
        logger.info(f"Button {callback_data} transitioned from {old_state.value} to {new_state.value}")
    
    def create_feature_showcase_buttons(self, features: List[Dict[str, Any]]) -> ButtonGrid:
        """Create buttons showcasing premium features with visual hierarchy."""
        grid = self.create_grid(max_buttons_per_row=1)  # Full-width for impact
        
        for feature in features:
            premium_indicator = "⭐ " if feature.get("premium") else ""
            new_indicator = "🆕 " if feature.get("new") else ""
            
            button_text = f"{premium_indicator}{new_indicator}{feature['name']}"
            
            button = self.create_button(
                text=button_text,
                callback_data=f"feature:{feature['id']}",
                emoji=feature.get("emoji", "✨")
            )
            
            # Add metadata for feature details
            self.set_button_metadata(button.callback_data, {
                "description": feature.get("description", ""),
                "premium": feature.get("premium", False),
                "tier_required": feature.get("tier_required", "starter")
            })
            
            grid.add_button(button)
        
        return grid