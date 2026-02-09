"""MyPoolr creation workflow handlers."""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from loguru import logger

from utils.button_manager import ButtonManager
from utils.state_manager import StateManager, ConversationState
from utils.ui_components import ProgressIndicator, InteractiveCard
from utils.formatters import MessageFormatter, EmojiHelper
from utils.feedback_system import VisualFeedbackManager


# Conversation states
SELECTING_COUNTRY = 1
ENTERING_NAME = 2
ENTERING_AMOUNT = 3
SELECTING_FREQUENCY = 4
SELECTING_TIER = 5
ENTERING_MEMBER_LIMIT = 6
CONFIRMING_DETAILS = 7


async def start_mypoolr_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start MyPoolr creation workflow with country selection."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    # Initialize creation state
    if state_manager:
        state_manager.start_conversation(user_id, ConversationState.CREATING_MYPOOLR)
    
    # Progress indicator
    progress = ProgressIndicator.create_step_indicator(
        current_step=1,
        total_steps=6,
        step_names=["Country", "Details", "Amount", "Frequency", "Tier", "Confirm"]
    )
    
    creation_text = f"""
**Create MyPoolr** — Step 1 of 6

{progress}

**Select Your Country**

Choose your country to enable local features, currency, and payment methods.

*Available Countries:*
    """.strip()
    
    # Create country selection buttons with flags
    countries = [
        {"code": "KE", "name": "Kenya", "flag": "🇰🇪", "currency": "KES"},
        {"code": "UG", "name": "Uganda", "flag": "🇺🇬", "currency": "UGX"},
        {"code": "TZ", "name": "Tanzania", "flag": "🇹🇿", "currency": "TZS"},
        {"code": "RW", "name": "Rwanda", "flag": "🇷🇼", "currency": "RWF"},
        {"code": "NG", "name": "Nigeria", "flag": "🇳🇬", "currency": "NGN"},
        {"code": "GH", "name": "Ghana", "flag": "🇬🇭", "currency": "GHS"}
    ]
    
    grid = button_manager.create_grid(max_buttons_per_row=2)
    
    for country in countries:
        grid.add_button(button_manager.create_button(
            f"{country['flag']} {country['name']}",
            f"country:{country['code']}"
        ))
    
    # Add navigation
    grid.add_row([
        button_manager.create_button("Cancel", "cancel_creation")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=creation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=creation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    return SELECTING_COUNTRY

async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country selection and move to name entry."""
    query = update.callback_query
    await query.answer()
    
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    if query.data.startswith("country:"):
        country_code = query.data.replace("country:", "")
        
        # Store country selection
        if state_manager:
            state_manager.update_data(user_id, {"country": country_code})
        
        # Progress indicator
        progress = ProgressIndicator.create_step_indicator(
            current_step=2,
            total_steps=6,
            step_names=["Country", "Details", "Amount", "Frequency", "Tier", "Confirm"]
        )
        
        country_names = {
            "KE": "Kenya 🇰🇪", "UG": "Uganda 🇺🇬", "TZ": "Tanzania 🇹🇿",
            "RW": "Rwanda 🇷🇼", "NG": "Nigeria 🇳🇬", "GH": "Ghana 🇬🇭"
        }
        
        name_text = f"""
📝 *Create MyPoolr - Step 2/6*

{progress}

*Group Details*

Selected Country: {country_names.get(country_code, country_code)}

Now, let's set up your group details:

*Group Name:*
Enter a name for your MyPoolr group (e.g., "Office Savings", "Family Circle")

💡 *Tips:*
• Choose a memorable name
• Keep it under 30 characters
• Make it descriptive for members
        """.strip()
        
        # Create skip/back buttons
        grid = button_manager.create_grid()
        grid.add_row([
            button_manager.create_button("⬅️ Back", "back_to_country", emoji="⬅️"),
            button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await query.edit_message_text(
            text=name_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        return ENTERING_NAME
    
    return SELECTING_COUNTRY


async def handle_name_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle group name entry and move to amount entry."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    group_name = update.message.text.strip()
    
    # Validate name
    if len(group_name) < 3:
        await update.message.reply_text(
            "⚠️ Group name must be at least 3 characters long. Please try again:"
        )
        return ENTERING_NAME
    
    if len(group_name) > 30:
        await update.message.reply_text(
            "⚠️ Group name must be under 30 characters. Please try again:"
        )
        return ENTERING_NAME
    
    # Store name
    if state_manager:
        state_manager.update_data(user_id, {"name": group_name})
    
    # Progress indicator
    progress = ProgressIndicator.create_step_indicator(
        current_step=3,
        total_steps=6,
        step_names=["Country", "Details", "Amount", "Frequency", "Tier", "Confirm"]
    )
    
    amount_text = f"""
💰 *Create MyPoolr - Step 3/6*

{progress}

*Contribution Amount*

Group Name: "{MessageFormatter.escape_markdown(group_name)}" ✅

Enter the contribution amount each member will pay per rotation:

*Examples:*
• KES 1,000 (Small group)
• KES 5,000 (Medium group)  
• KES 10,000 (Large group)

💡 *Tips:*
• Choose an amount everyone can afford
• Consider the rotation frequency
• Higher amounts need higher security deposits

Enter amount (numbers only):
    """.strip()
    
    # Create navigation buttons
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("⬅️ Back", "back_to_name", emoji="⬅️"),
        button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.message.reply_text(
        text=amount_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    return ENTERING_AMOUNT
async def handle_amount_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle contribution amount entry and move to frequency selection."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    amount_text = update.message.text.strip().replace(",", "")
    
    # Validate amount
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > 1000000:  # 1 million limit
            raise ValueError("Amount too large")
    except ValueError:
        await update.message.reply_text(
            "⚠️ Please enter a valid amount (numbers only, e.g., 5000):"
        )
        return ENTERING_AMOUNT
    
    # Store amount
    if state_manager:
        state_manager.update_data(user_id, {"amount": amount})
    
    # Progress indicator
    progress = ProgressIndicator.create_step_indicator(
        current_step=4,
        total_steps=6,
        step_names=["Country", "Details", "Amount", "Frequency", "Tier", "Confirm"]
    )
    
    frequency_text = f"""
📅 *Create MyPoolr - Step 4/6*

{progress}

*Rotation Frequency*

Contribution Amount: {MessageFormatter.format_currency(amount)} ✅

How often should rotations happen?

🔄 *Frequency Options:*
    """.strip()
    
    # Create frequency selection buttons
    grid = button_manager.create_grid(max_buttons_per_row=1)
    
    frequencies = [
        {
            "id": "daily",
            "name": "Daily",
            "emoji": "📅",
            "description": "Every day (high activity)"
        },
        {
            "id": "weekly", 
            "name": "Weekly",
            "emoji": "📆",
            "description": "Every week (recommended)"
        },
        {
            "id": "monthly",
            "name": "Monthly", 
            "emoji": "🗓️",
            "description": "Every month (relaxed pace)"
        }
    ]
    
    for freq in frequencies:
        grid.add_row([
            button_manager.create_button(
                f"{freq['name']} - {freq['description']}",
                f"frequency:{freq['id']}",
                emoji=freq['emoji']
            )
        ])
    
    # Add navigation
    grid.add_row([
        button_manager.create_button("⬅️ Back", "back_to_amount", emoji="⬅️"),
        button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    await update.message.reply_text(
        text=frequency_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    return SELECTING_FREQUENCY


async def handle_frequency_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle frequency selection and move to tier selection."""
    query = update.callback_query
    await query.answer()
    
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    if query.data.startswith("frequency:"):
        frequency = query.data.replace("frequency:", "")
        
        # Store frequency
        if state_manager:
            state_manager.update_data(user_id, {"frequency": frequency})
        
        # Progress indicator
        progress = ProgressIndicator.create_step_indicator(
            current_step=5,
            total_steps=6,
            step_names=["Country", "Details", "Amount", "Frequency", "Tier", "Confirm"]
        )
        
        frequency_names = {
            "daily": "Daily 📅",
            "weekly": "Weekly 📆", 
            "monthly": "Monthly 🗓️"
        }
        
        tier_text = f"""
💎 *Create MyPoolr - Step 5/6*

{progress}

*Select Your Tier*

Rotation Frequency: {frequency_names.get(frequency, frequency)} ✅

Choose your MyPoolr tier to determine group limits and features:

⭐ *Available Tiers:*
        """.strip()
        
        # Create tier selection with detailed info
        grid = button_manager.create_grid(max_buttons_per_row=1)
        
        tiers = [
            {
                "id": "starter",
                "name": "Starter",
                "price": 0,
                "max_groups": 1,
                "max_members": 10,
                "features": ["Basic notifications", "Standard support"]
            },
            {
                "id": "essential", 
                "name": "Essential",
                "price": 2,
                "max_groups": 3,
                "max_members": 25,
                "features": ["Priority notifications", "Advanced analytics", "Priority support"]
            },
            {
                "id": "advanced",
                "name": "Advanced", 
                "price": 5,
                "max_groups": 10,
                "max_members": 50,
                "features": ["Custom schedules", "Export reports", "API access"]
            },
            {
                "id": "extended",
                "name": "Extended",
                "price": 10, 
                "max_groups": "Unlimited",
                "max_members": "Unlimited",
                "features": ["White-label", "Dedicated support", "Custom integrations"]
            }
        ]
        
        for tier in tiers:
            price_text = "Free" if tier["price"] == 0 else f"${tier['price']}/month"
            members_text = str(tier["max_members"]) if tier["max_members"] != "Unlimited" else "∞"
            groups_text = str(tier["max_groups"]) if tier["max_groups"] != "Unlimited" else "∞"
            
            button_text = f"{tier['name']} - {price_text}"
            
            grid.add_row([
                button_manager.create_button(
                    button_text,
                    f"tier:{tier['id']}",
                    emoji="⭐" * (tiers.index(tier) + 1)
                )
            ])
        
        # Add navigation
        grid.add_row([
            button_manager.create_button("⬅️ Back", "back_to_frequency", emoji="⬅️"),
            button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await query.edit_message_text(
            text=tier_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        return SELECTING_TIER
    
    return SELECTING_FREQUENCY
async def handle_tier_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle tier selection and move to member limit entry."""
    query = update.callback_query
    await query.answer()
    
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    if query.data.startswith("tier:"):
        tier = query.data.replace("tier:", "")
        
        # Store tier
        if state_manager:
            state_manager.update_data(user_id, {"tier": tier})
        
        # Get tier limits
        tier_limits = {
            "starter": {"max_members": 10, "max_groups": 1},
            "essential": {"max_members": 25, "max_groups": 3},
            "advanced": {"max_members": 50, "max_groups": 10},
            "extended": {"max_members": 100, "max_groups": 999}
        }
        
        limits = tier_limits.get(tier, tier_limits["starter"])
        
        # Progress indicator
        progress = ProgressIndicator.create_step_indicator(
            current_step=6,
            total_steps=6,
            step_names=["Country", "Details", "Amount", "Frequency", "Tier", "Confirm"]
        )
        
        tier_names = {
            "starter": "Starter (Free)",
            "essential": "Essential ($2/mo)",
            "advanced": "Advanced ($5/mo)",
            "extended": "Extended ($10/mo)"
        }
        
        member_text = f"""
👥 *Create MyPoolr - Step 6/6*

{progress}

*Member Limit*

Selected Tier: {tier_names.get(tier, tier)} ✅

How many members can join this group?

*Tier Limit:* Up to {limits['max_members']} members

💡 *Recommendations:*
• Start small (5-8 members) for first group
• More members = longer rotation cycles
• Consider security deposit amounts

Enter member limit (3-{limits['max_members']}):
        """.strip()
        
        # Create quick selection buttons
        grid = button_manager.create_grid()
        
        # Suggest common member counts
        suggestions = []
        if limits['max_members'] >= 5:
            suggestions.append(5)
        if limits['max_members'] >= 8:
            suggestions.append(8)
        if limits['max_members'] >= 10:
            suggestions.append(10)
        if limits['max_members'] >= 15:
            suggestions.append(15)
        
        suggestion_buttons = []
        for count in suggestions:
            suggestion_buttons.append(
                button_manager.create_button(
                    f"{count} members",
                    f"members:{count}",
                    emoji="👥"
                )
            )
        
        # Add suggestion buttons in rows of 2
        for i in range(0, len(suggestion_buttons), 2):
            row_buttons = suggestion_buttons[i:i+2]
            grid.add_row(row_buttons)
        
        # Add navigation
        grid.add_row([
            button_manager.create_button("⬅️ Back", "back_to_tier", emoji="⬅️"),
            button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await query.edit_message_text(
            text=member_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        return ENTERING_MEMBER_LIMIT
    
    return SELECTING_TIER


async def handle_member_limit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle member limit entry and show confirmation."""
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    # Handle both text input and button selection
    if update.callback_query and update.callback_query.data.startswith("members:"):
        member_limit = int(update.callback_query.data.replace("members:", ""))
        await update.callback_query.answer()
    else:
        try:
            member_limit = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "⚠️ Please enter a valid number for member limit:"
            )
            return ENTERING_MEMBER_LIMIT
    
    # Validate member limit
    if member_limit < 3:
        error_msg = "⚠️ Minimum 3 members required. Please try again:"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return ENTERING_MEMBER_LIMIT
    
    # Get user's current tier limits (this would come from backend)
    tier_limits = {"starter": 10, "essential": 25, "advanced": 50, "extended": 100}
    user_data = state_manager.get_state(user_id).data if state_manager else {}
    user_tier = user_data.get("tier", "starter")
    max_allowed = tier_limits.get(user_tier, 10)
    
    if member_limit > max_allowed:
        error_msg = f"⚠️ Your {user_tier} tier allows maximum {max_allowed} members. Please try again:"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        return ENTERING_MEMBER_LIMIT
    
    # Store member limit
    if state_manager:
        state_manager.update_data(user_id, {"member_limit": member_limit})
        user_data = state_manager.get_state(user_id).data
    
    # Show confirmation with all details
    confirmation_text = f"""
✅ *MyPoolr Creation Summary*

Review your group details before creating:

🎯 *Group Details:*
• Name: {MessageFormatter.escape_markdown(user_data.get('name', 'Unknown'))}
• Country: {user_data.get('country', 'Unknown')} 
• Contribution: {MessageFormatter.format_currency(user_data.get('amount', 0))}
• Frequency: {user_data.get('frequency', 'Unknown').title()}
• Member Limit: {member_limit} members
• Tier: {user_data.get('tier', 'starter').title()}

🔒 *Security Features:*
• Security deposits: Auto-calculated
• No-loss guarantee: Enabled
• Two-party confirmation: Required
• Account lock-in: After payout

📋 *Next Steps:*
1. Create group and get invitation link
2. Share link with potential members
3. Members join and pay security deposits
4. Start first rotation when ready!

Ready to create your MyPoolr?
    """.strip()
    
    # Create confirmation buttons
    grid = button_manager.create_grid()
    grid.add_row([
        button_manager.create_button("🚀 Create MyPoolr", "confirm_create", emoji="🚀")
    ])
    grid.add_row([
        button_manager.create_button("✏️ Edit Details", "edit_details", emoji="✏️"),
        button_manager.create_button("❌ Cancel", "cancel_creation", emoji="❌")
    ])
    
    keyboard = button_manager.build_keyboard(grid)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=confirmation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=confirmation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    return CONFIRMING_DETAILS


async def handle_creation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle final creation confirmation."""
    query = update.callback_query
    await query.answer()
    
    button_manager: ButtonManager = context.bot_data.get("button_manager")
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    if query.data == "confirm_create":
        # Get all stored data
        user_data = state_manager.get_state(user_id).data if state_manager else {}
        
        # Show creation in progress
        await query.edit_message_text(
            "🚀 Creating your MyPoolr...\n\n"
            "⏳ Setting up group structure\n"
            "⏳ Generating invitation link\n" 
            "⏳ Configuring security settings"
        )
        
        # Simulate creation process (would call backend API)
        import asyncio
        await asyncio.sleep(2)
        
        # Generate mock invitation link
        import random
        invitation_code = f"MYPOOLR-{random.randint(10000, 99999)}-{random.randint(10000, 99999)}"
        invitation_link = f"https://t.me/mypoolr_bot?start=invite_{invitation_code}"
        
        success_text = f"""
🎉 *MyPoolr Created Successfully!*

Your "{MessageFormatter.escape_markdown(user_data.get('name', 'MyPoolr'))}" group is ready!

🔗 *Invitation Details:*
Code: `{invitation_code}`
Link: {invitation_link}

📤 *Share with Members:*
Send the link above to invite members to your group.

📋 *What's Next:*
1. Share invitation link with potential members
2. Members will join and pay security deposits
3. You can start the first rotation when ready
4. Manage your group from "My Groups" menu

🎯 *Group Summary:*
• Contribution: {MessageFormatter.format_currency(user_data.get('amount', 0))}
• Frequency: {user_data.get('frequency', 'Unknown').title()}
• Max Members: {user_data.get('member_limit', 0)}
        """.strip()
        
        # Create action buttons
        grid = button_manager.create_grid()
        grid.add_row([
            button_manager.create_button("📤 Share Link", f"share_link:{invitation_code}", emoji="📤"),
            button_manager.create_button("👥 Manage Group", f"manage_group:{invitation_code}", emoji="👥")
        ])
        grid.add_row([
            button_manager.create_button("🏠 Main Menu", "main_menu", emoji="🏠")
        ])
        
        keyboard = button_manager.build_keyboard(grid)
        
        await query.edit_message_text(
            text=success_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Clear conversation state
        if state_manager:
            state_manager.end_conversation(user_id)
        
        return ConversationHandler.END
    
    return CONFIRMING_DETAILS


async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel MyPoolr creation."""
    query = update.callback_query
    await query.answer()
    
    state_manager: StateManager = context.bot_data.get("state_manager")
    user_id = update.effective_user.id
    
    # Clear conversation state
    if state_manager:
        state_manager.end_conversation(user_id)
    
    await query.edit_message_text(
        "❌ MyPoolr creation cancelled.\n\n"
        "You can start again anytime from the main menu!",
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END