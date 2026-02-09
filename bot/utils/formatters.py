"""Text formatting utilities for MyPoolr Telegram Bot."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re


class MessageFormatter:
    """Utilities for formatting Telegram messages."""
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape special characters for Markdown formatting."""
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    
    @staticmethod
    def format_currency(amount: float, currency: str = "KES") -> str:
        """Format currency amount."""
        return f"{currency} {amount:,.2f}"
    
    @staticmethod
    def format_datetime(dt: datetime, include_time: bool = True) -> str:
        """Format datetime for display."""
        if include_time:
            return dt.strftime("%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d")
    
    @staticmethod
    def format_time_remaining(target_time: datetime) -> str:
        """Format time remaining until target."""
        now = datetime.now()
        if target_time <= now:
            return "⏰ Overdue"
        
        delta = target_time - now
        
        if delta.days > 0:
            return f"⏳ {delta.days} days remaining"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"⏳ {hours} hours remaining"
        else:
            minutes = delta.seconds // 60
            return f"⏳ {minutes} minutes remaining"
    
    @staticmethod
    def format_progress_bar(current: int, total: int, width: int = 10) -> str:
        """Create a progress bar."""
        if total == 0:
            return "▱" * width
        
        filled = int((current / total) * width)
        empty = width - filled
        
        return "▰" * filled + "▱" * empty
    
    @staticmethod
    def format_member_list(members: List[Dict[str, Any]]) -> str:
        """Format member list for display."""
        if not members:
            return "No members yet."
        
        formatted_members = []
        for i, member in enumerate(members, 1):
            status_emoji = "✅" if member.get("security_deposit_paid") else "⏳"
            name = MessageFormatter.escape_markdown(member.get("name", "Unknown"))
            formatted_members.append(f"{i}. {status_emoji} {name}")
        
        return "\n".join(formatted_members)
    
    @staticmethod
    def format_mypoolr_summary(mypoolr: Dict[str, Any]) -> str:
        """Format MyPoolr summary for display."""
        name = MessageFormatter.escape_markdown(mypoolr.get("name", "Unknown"))
        amount = MessageFormatter.format_currency(mypoolr.get("contribution_amount", 0))
        frequency = mypoolr.get("rotation_frequency", "unknown").title()
        member_count = mypoolr.get("member_count", 0)
        member_limit = mypoolr.get("member_limit", 0)
        
        return f"""
🎯 *{name}*

💰 Contribution: {amount}
📅 Frequency: {frequency}
👥 Members: {member_count}/{member_limit}
        """.strip()
    
    @staticmethod
    def format_contribution_request(contribution: Dict[str, Any]) -> str:
        """Format contribution request for display."""
        amount = MessageFormatter.format_currency(contribution.get("amount", 0))
        recipient = MessageFormatter.escape_markdown(contribution.get("recipient_name", "Unknown"))
        due_date = contribution.get("due_date")
        
        time_info = ""
        if due_date:
            due_dt = datetime.fromisoformat(due_date)
            time_info = f"\n{MessageFormatter.format_time_remaining(due_dt)}"
        
        return f"""
💸 *Contribution Request*

Amount: {amount}
Recipient: {recipient}{time_info}
        """.strip()
    
    @staticmethod
    def format_tier_comparison(tiers: List[Dict[str, Any]]) -> str:
        """Format tier comparison table."""
        if not tiers:
            return "No tiers available."
        
        formatted_tiers = []
        for tier in tiers:
            name = tier.get("name", "Unknown")
            price = tier.get("price", 0)
            max_groups = tier.get("max_groups", 0)
            features = tier.get("features", [])
            
            price_text = "Free" if price == 0 else MessageFormatter.format_currency(price)
            
            tier_text = f"""
*{name}* - {price_text}
📊 Max Groups: {max_groups}
✨ Features: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}
            """.strip()
            
            formatted_tiers.append(tier_text)
        
        return "\n\n".join(formatted_tiers)


class EmojiHelper:
    """Helper class for consistent emoji usage."""
    
    # Status emojis
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    
    # Action emojis
    CREATE = "➕"
    EDIT = "✏️"
    DELETE = "🗑️"
    VIEW = "👁️"
    SHARE = "📤"
    
    # MyPoolr emojis
    MONEY = "💰"
    GROUP = "👥"
    CALENDAR = "📅"
    TARGET = "🎯"
    SECURITY = "🔒"
    
    # Navigation emojis
    HOME = "🏠"
    BACK = "⬅️"
    NEXT = "➡️"
    UP = "⬆️"
    DOWN = "⬇️"
    
    # Country flags (common ones)
    FLAGS = {
        "KE": "🇰🇪",  # Kenya
        "UG": "🇺🇬",  # Uganda
        "TZ": "🇹🇿",  # Tanzania
        "RW": "🇷🇼",  # Rwanda
        "NG": "🇳🇬",  # Nigeria
        "GH": "🇬🇭",  # Ghana
        "ZA": "🇿🇦",  # South Africa
    }
    
    @classmethod
    def get_flag(cls, country_code: str) -> str:
        """Get flag emoji for country code."""
        return cls.FLAGS.get(country_code.upper(), "🏳️")