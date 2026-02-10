# Requirements Document

## Introduction

This document specifies the requirements for fixing callback handler routing issues in the MyPoolr Telegram bot. Users currently encounter "Feature not available" errors when clicking certain buttons during conversation workflows (such as MyPoolr creation) because the main callback router does not have routes for all callbacks used in conversation flows. The system needs to properly route all conversation-related callbacks and provide better error handling for unhandled callbacks.

## Glossary

- **Callback_Router**: The main button_callback function in bot/handlers/callbacks.py that routes callback queries to appropriate handler functions
- **Conversation_Handler**: A Telegram ConversationHandler that manages multi-step conversation workflows with state transitions
- **Callback_Query**: A Telegram update triggered when a user clicks an inline keyboard button
- **Conversation_Callback**: A callback_data string used within a ConversationHandler's state machine (e.g., cancel_creation, country:XX, confirm_create)
- **Main_Callback**: A callback_data string handled by the main Callback_Router outside of conversation flows
- **Button_Manager**: The utility class that creates and manages inline keyboard buttons
- **State_Manager**: The utility class that manages user conversation state

## Requirements

### Requirement 1: Route Conversation Cancellation Callbacks

**User Story:** As a user, I want to cancel a MyPoolr creation workflow at any step, so that I can exit the process and return to the main menu without encountering errors.

#### Acceptance Criteria

1. WHEN a user clicks a cancel button during MyPoolr creation, THE Callback_Router SHALL route the cancel_creation callback to the appropriate handler
2. WHEN the cancel_creation callback is processed, THE System SHALL clear the user's conversation state
3. WHEN the cancel_creation callback is processed, THE System SHALL display the main menu to the user
4. WHEN a user is not in an active conversation, THE System SHALL handle cancel_creation gracefully without errors

### Requirement 2: Route Conversation Navigation Callbacks

**User Story:** As a user, I want to navigate backward through the MyPoolr creation steps, so that I can correct information without starting over.

#### Acceptance Criteria

1. WHEN a user clicks a back button during MyPoolr creation, THE Callback_Router SHALL route back_to_* callbacks to the appropriate handler
2. WHEN a back_to_country callback is received, THE System SHALL return the user to the country selection step
3. WHEN a back_to_name callback is received, THE System SHALL return the user to the name entry step
4. WHEN a back_to_amount callback is received, THE System SHALL return the user to the amount entry step
5. WHEN a back_to_frequency callback is received, THE System SHALL return the user to the frequency selection step
6. WHEN a back_to_tier callback is received, THE System SHALL return the user to the tier selection step

### Requirement 3: Route Conversation Confirmation Callbacks

**User Story:** As a user, I want to confirm my MyPoolr creation details, so that the system creates my group with the correct settings.

#### Acceptance Criteria

1. WHEN a user clicks the confirm button, THE Callback_Router SHALL route the confirm_create callback to the appropriate handler
2. WHEN a user clicks the edit details button, THE Callback_Router SHALL route the edit_details callback to the appropriate handler
3. WHEN the confirm_create callback is processed, THE System SHALL create the MyPoolr group with the stored user data
4. WHEN the edit_details callback is processed, THE System SHALL allow the user to modify their group details

### Requirement 4: Provide Fallback Error Handling

**User Story:** As a user, I want to receive helpful error messages when I click an unhandled button, so that I understand what went wrong and how to proceed.

#### Acceptance Criteria

1. WHEN a callback is not routed by the Callback_Router, THE System SHALL check if the callback is registered with the Button_Manager
2. WHEN a callback is registered with the Button_Manager, THE System SHALL execute the registered callback function
3. WHEN a callback is neither routed nor registered, THE System SHALL display a user-friendly error message
4. WHEN displaying an error message, THE System SHALL include the callback_data for debugging purposes
5. WHEN displaying an error message, THE System SHALL provide a button to return to the main menu

### Requirement 5: Maintain Conversation Handler Independence

**User Story:** As a developer, I want ConversationHandlers to manage their own callback routing, so that conversation flows remain encapsulated and maintainable.

#### Acceptance Criteria

1. WHEN a callback is part of an active conversation, THE Conversation_Handler SHALL process the callback before the main Callback_Router
2. WHEN a callback is processed by a Conversation_Handler, THE main Callback_Router SHALL not receive the callback
3. WHEN a conversation ends, THE System SHALL ensure subsequent callbacks are routed through the main Callback_Router
4. WHEN adding new conversation callbacks, THE System SHALL not require modifications to the main Callback_Router

### Requirement 6: Log Callback Routing Events

**User Story:** As a developer, I want detailed logging of callback routing decisions, so that I can debug routing issues and monitor system behavior.

#### Acceptance Criteria

1. WHEN a callback is received, THE System SHALL log the callback_data and user_id
2. WHEN a callback is routed to a handler, THE System SHALL log which handler processed the callback
3. WHEN a callback is not routed, THE System SHALL log the unhandled callback with warning level
4. WHEN a callback handler raises an exception, THE System SHALL log the error with stack trace

### Requirement 7: Handle Conversation State Transitions

**User Story:** As a user, I want the system to maintain my conversation state correctly, so that I can complete multi-step workflows without losing my progress.

#### Acceptance Criteria

1. WHEN a user starts a conversation, THE System SHALL initialize conversation state for that user
2. WHEN a user completes a conversation step, THE System SHALL update the conversation state
3. WHEN a user cancels a conversation, THE System SHALL clear the conversation state
4. WHEN a conversation times out, THE System SHALL clear the conversation state and notify the user

### Requirement 8: Support Multiple Concurrent Conversations

**User Story:** As a developer, I want to support multiple conversation types simultaneously, so that users can access different workflows without conflicts.

#### Acceptance Criteria

1. WHEN multiple ConversationHandlers are registered, THE System SHALL route callbacks to the correct conversation based on user state
2. WHEN a user is in one conversation, THE System SHALL prevent starting another conversation until the first completes or is cancelled
3. WHEN a user completes a conversation, THE System SHALL allow starting a new conversation immediately
4. WHEN conversations have overlapping callback patterns, THE System SHALL prioritize the active conversation's handlers
