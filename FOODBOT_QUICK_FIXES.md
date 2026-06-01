# FoodBotAIHandler - Quick Fix Guide

## Quick Implementation Reference

### FIX #1: JSON Parsing Error Handling (CRITICAL)

**File**: `api/services/ai/orchestrator.py`
**Line**: 164
**Time**: 5 minutes

```python
# ❌ BEFORE (Vulnerable to crashes)
for tool_call in response_message.tool_calls[:5]:
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)  # Can crash here!

# ✅ AFTER (Robust)
for tool_call in response_message.tool_calls[:5]:
    function_name = tool_call.function.name
    try:
        function_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON from LLM for tool {function_name}: {e}")
        print(f"Raw arguments: {tool_call.function.arguments}")
        continue  # Skip this tool call and continue with next
```

---

### FIX #2: Tool Validation & User Parameter (CRITICAL)

**File**: `api/services/ai/orchestrator.py`
**Line**: 167-174
**Time**: 10 minutes

```python
# ❌ BEFORE (Can crash with KeyError or TypeError)
function_args["user"] = self.user

try:
    function_response = self.tool_functions[function_name](**function_args)
    print("Function response:", function_response)
except Exception as e:
    print(f"Error executing tool {function_name}: {e}")

# ✅ AFTER (Validates first)
# Validate tool exists
if function_name not in self.tool_functions:
    print(f"Error: Tool '{function_name}' not found in registry")
    print(f"Available tools: {list(self.tool_functions.keys())}")
    continue

# Add user parameter
function_args["user"] = self.user

# Execute with proper error handling
try:
    function_response = self.tool_functions[function_name](**function_args)
    print(f"Tool '{function_name}' executed successfully: {function_response}")
except TypeError as e:
    print(f"Error: Invalid parameters for '{function_name}': {e}")
    print(f"Expected parameters from schema needed")
except Exception as e:
    print(f"Error: Unexpected error in '{function_name}': {e}")
    import traceback
    traceback.print_exc()
```

---

### FIX #3: Fix Return Type (CRITICAL)

**File**: `api/services/ai/orchestrator.py`
**Line**: 114, 158, 176
**Time**: 15 minutes

```python
# ❌ BEFORE (Inconsistent return types)
def process_message(self) -> str:
    # ...
    if not response_message.tool_calls:
        return response_message.content  # str or None

    # ... execute tools ...
    return None  # Always None if tools executed

# ✅ AFTER (Consistent and clear)
def process_message(self) -> Dict:
    """
    Process user message and return response.

    Returns:
        dict with keys:
        - 'type': 'text' | 'tool_executed' | 'error'
        - 'content': str (response or error message)
        - 'success': bool (True if no errors)
        - 'tools_executed': List[str] (names of tools that ran)
    """
    tools_executed = []

    messages = self.get_conversation_history()
    response = self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message

    # Handle text response without tools
    if not response_message.tool_calls:
        return {
            'type': 'text',
            'content': response_message.content,
            'success': True,
            'tools_executed': []
        }

    # Handle tool execution
    for tool_call in response_message.tool_calls[:5]:
        # ... validation and execution ...
        if function_name in self.tool_functions:
            tools_executed.append(function_name)

    return {
        'type': 'tool_executed',
        'content': f"Executed {len(tools_executed)} tool(s)",
        'success': len(tools_executed) > 0,
        'tools_executed': tools_executed
    }
```

---

### FIX #4: Fix Essential Tools Configuration (HIGH)

**File**: `api/services/ai/orchestrator.py`
**Line**: 28-34
**Time**: 5 minutes

```python
# ❌ BEFORE (Hardcoded with wrong tool name)
self.essential_tools = [
    "generate_meal_recommendations",  # ❌ This tool doesn't exist!
    "place_order",
    "contact_support"
]

# ✅ AFTER (Correct names from tool definitions)
self.essential_tools = [
    "meal_recommendations",  # ✅ Correct name from tool_definitions.py
    "place_order",
    "contact_support"
]

# BONUS: Add validation
for tool_name in self.essential_tools:
    tool_exists = any(
        t.get("function", {}).get("name") == tool_name
        for t in self.all_tools
    )
    if not tool_exists:
        print(f"Warning: Essential tool '{tool_name}' not found in tool definitions")
```

---

### FIX #5: Add Logging (HIGH)

**File**: `api/services/ai/orchestrator.py`
**Line**: 1-4
**Time**: 10 minutes

```python
# ✅ ADD AT TOP OF FILE
import logging

logger = logging.getLogger(__name__)

# ✅ REPLACE print() with logger calls throughout:

# ❌ BEFORE
print("Tool call detected:", response_message.tool_calls)

# ✅ AFTER
logger.info("Tool calls detected", extra={
    "count": len(response_message.tool_calls),
    "tools": [tc.function.name for tc in response_message.tool_calls]
})

# ❌ BEFORE
print(f"Error executing tool {function_name}: {e}")

# ✅ AFTER
logger.error(f"Tool execution failed", extra={
    "tool_name": function_name,
    "error": str(e),
    "user_id": self.user.id
}, exc_info=True)
```

---

### FIX #6: Add Context Window Management (MEDIUM)

**File**: `api/services/ai/orchestrator.py`
**Line**: 77-112
**Time**: 20 minutes

```python
# ✅ ADD METHOD
def _count_tokens(self, text: str) -> int:
    """Rough token estimate: ~4 chars per token"""
    return len(text) // 4

def get_conversation_history(self) -> List[Dict]:
    """Get conversation history respecting token limits."""
    # System message always included
    messages = [{
        "role": "system",
        "content": "You are a WhatsApp food bot..."
    }]

    # Track token usage
    max_tokens = 3500  # Leave room for response
    current_tokens = self._count_tokens(messages[0]["content"])

    if self.reply_message and self.sender_message:
        # ... existing code ...
        messages.append(...)
        messages.append(...)
        current_tokens += self._count_tokens(self.reply_message.get_content_meta())
        current_tokens += self._count_tokens(self.sender_message.get_content_meta())
    else:
        # Get recent messages from database
        db_messages = Message.objects.filter(user=self.user).order_by('-created_at')[:5]
        for msg in reversed(db_messages):
            msg_content = msg.get_content_meta()
            msg_tokens = self._count_tokens(msg_content)

            # Stop if adding this message would exceed limit
            if current_tokens + msg_tokens > max_tokens:
                logger.warning(f"Context window limit reached for user {self.user.id}")
                break

            if msg.role == RoleChoices.USER:
                messages.append({"role": "user", "content": msg_content})
            else:
                messages.append({"role": "assistant", "content": msg_content})

            current_tokens += msg_tokens

    logger.info(f"Built conversation history", extra={
        "user_id": self.user.id,
        "message_count": len(messages),
        "estimated_tokens": current_tokens
    })

    return messages
```

---

### FIX #7: Add Initialization Validation (MEDIUM)

**File**: `api/services/ai/orchestrator.py`
**Line**: 14-34
**Time**: 10 minutes

```python
# ✅ ADD VALIDATION IN __init__
def __init__(self, user: User, ...):
    self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    self.model = model
    self.user = user
    # ... rest of init ...

    # ✅ NEW: Validate tool registration
    self._validate_tools()

# ✅ ADD NEW METHOD
def _validate_tools(self) -> None:
    """Validate all tool definitions have registered handlers."""
    missing_tools = []

    for tool in self.all_tools:
        tool_name = tool.get("function", {}).get("name", "")
        if not tool_name:
            logger.warning("Found tool with no name in definition")
            continue

        if tool_name not in self.tool_functions:
            missing_tools.append(tool_name)

    if missing_tools:
        logger.error(f"Missing tool handlers", extra={
            "missing_tools": missing_tools,
            "registered_tools": list(self.tool_functions.keys())
        })
        raise ValueError(f"Tools not registered: {missing_tools}")

    # Validate essential tools exist
    for essential_tool in self.essential_tools:
        if essential_tool not in [t.get("function", {}).get("name") for t in self.all_tools]:
            logger.warning(f"Essential tool not found: {essential_tool}")

    logger.info(f"Tool validation passed", extra={
        "total_tools": len(self.all_tools),
        "registered_handlers": len(self.tool_functions)
    })
```

---

## Implementation Order

```bash
# 1. Add logging infrastructure (fixes all files)
# ✅ 5 minutes
# Modify: imports, all print() → logger calls

# 2. Fix JSON parsing (lines 164-171)
# ✅ 5 minutes

# 3. Fix tool validation (lines 163-176)
# ✅ 10 minutes

# 4. Fix return type and structure
# ✅ 15 minutes

# 5. Fix essential tools names
# ✅ 5 minutes

# 6. Add initialization validation
# ✅ 10 minutes

# 7. Add context window management
# ✅ 20 minutes

# TOTAL: ~70 minutes = 1 hour 10 minutes for all critical fixes
```

---

## Testing After Fixes

```python
# Run unit tests
pytest tests_comprehensive_foodbot.py -v

# Test with mock user
from api.models.user import User
from api.services.ai.orchestrator import FoodBotAIHandler

user = User.objects.first()
handler = FoodBotAIHandler(user=user)

# This should now validate all tools
# And log detailed information

# Test JSON error handling
# (Difficult in real scenario, covered by unit tests)

# Test tool validation
handler.process_message()  # Should log if any tools missing
```

---

## File Checklist

- [ ] Fixed JSON parsing with try/except
- [ ] Added tool existence validation
- [ ] Added user parameter check
- [ ] Changed return type to Dict
- [ ] Fixed essential tools list (meal_recommendations not generate_meal_recommendations)
- [ ] Replaced all print() with logger calls
- [ ] Added _validate_tools() method
- [ ] Added context window token counting
- [ ] Added initialization validation
- [ ] Ran unit tests successfully
- [ ] Updated type hints
- [ ] Added docstrings to new methods

---

## Quick Validation

After implementing fixes, verify:

```python
# In Django shell
from api.services.ai.orchestrator import FoodBotAIHandler
from api.models.user import User

user = User.objects.first()
handler = FoodBotAIHandler(user=user)

# Should complete without errors and log initialization
# Should show all tools validated
# Should show conversation history with token estimate
```

