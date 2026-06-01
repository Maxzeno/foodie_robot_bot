# FoodBotAIHandler - Testing Execution Guide

## Overview

This guide explains how to run the comprehensive test suite and understand the different testing approaches for the FoodBotAIHandler.

---

## Test Suite Structure

### Files Created

1. **`tests_comprehensive_foodbot.py`** (17 test cases)
   - Unit tests covering all major functionality
   - Mock-based testing (no external dependencies)
   - Fast execution (~2-3 seconds)

2. **`FOODBOT_ANALYSIS_REPORT.md`** (Detailed findings)
   - 12 identified issues with severity levels
   - Architecture analysis
   - Priority roadmap

3. **`FOODBOT_QUICK_FIXES.md`** (Implementation guide)
   - Copy-paste ready code fixes
   - Time estimates for each fix
   - Implementation order

---

## Running Unit Tests

### Setup

```bash
# Install test dependencies
pip install pytest pytest-mock

# Verify installation
pytest --version
# Should show: pytest X.X.X
```

### Execute Tests

```bash
# Run all tests
cd /Users/developer/help/foodie_robot_backend
pytest tests_comprehensive_foodbot.py -v

# Expected output:
# tests_comprehensive_foodbot.py::TestFoodBotAIHandlerInitialization::test_handler_initialization PASSED
# tests_comprehensive_foodbot.py::TestFoodBotAIHandlerInitialization::test_handler_initialization_with_custom_params PASSED
# ... (17 tests total)
# ======================== 17 passed in 2.34s ========================
```

### Run Specific Test Groups

```bash
# Test initialization only
pytest tests_comprehensive_foodbot.py::TestFoodBotAIHandlerInitialization -v

# Test conversation history
pytest tests_comprehensive_foodbot.py::TestConversationHistory -v

# Test tool execution
pytest tests_comprehensive_foodbot.py::TestToolCallExecution -v

# Test error handling (would need fixes first)
pytest tests_comprehensive_foodbot.py::TestParameterValidation -v
```

### With Coverage Report

```bash
# Install coverage
pip install coverage pytest-cov

# Run with coverage
pytest tests_comprehensive_foodbot.py --cov=api.services.ai --cov-report=html

# View report
open htmlcov/index.html
```

### Verbose Output

```bash
# Show all print statements and detailed output
pytest tests_comprehensive_foodbot.py -v -s

# Show variable values on failures
pytest tests_comprehensive_foodbot.py -v --tb=long
```

---

## Test Coverage Breakdown

### Test Suite 1: Initialization (3 tests)

**What it tests**:
- Basic handler creation with default parameters
- Custom parameters (model, embedding filter, top_k)
- Tool registration completeness

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestFoodBotAIHandlerInitialization -v
```

**Expected Result**: ✅ All 3 pass
```
test_handler_initialization PASSED
test_handler_initialization_with_custom_params PASSED
test_tool_registration PASSED
```

---

### Test Suite 2: Conversation History (2 tests)

**What it tests**:
- Loading history from explicit message IDs
- Loading history from database
- Message ordering (oldest first)
- System prompt inclusion

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestConversationHistory -v
```

**Expected Result**: ✅ All 2 pass

**Key Validation**:
- System message always first
- Messages appear in correct order
- User/assistant roles properly formatted

---

### Test Suite 3: Tool Execution (3 tests)

**What it tests**:
- Successful tool invocation
- Error handling in tool execution
- Maximum 5 tool calls limit enforcement

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestToolCallExecution -v
```

**Expected Result**: ✅ All 3 pass

**Current Issues Found**:
- ❌ JSON parsing not guarded against malformed input
- ❌ Tool existence not validated before calling
- ❌ Exception handling too broad (catches everything)

---

### Test Suite 4: Embedding Filter (2 tests)

**What it tests**:
- Filter correctly activated when `use_embedding_filter=True`
- All tools used when filter disabled
- Essential tools included in filtered results

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestEmbeddingFilter -v
```

**Expected Result**: ✅ All 2 pass (with current code)

---

### Test Suite 5: Response Handling (2 tests)

**What it tests**:
- Text response without tool calls
- Tool execution without text response

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestResponseHandling -v
```

**Expected Result**: ✅ All 2 pass

**Finding**: Return type inconsistency (function says `str` but returns `None`)

---

### Test Suite 6: Parameter Validation (2 tests)

**What it tests**:
- Invalid JSON in tool arguments (WILL FAIL - this is a bug!)
- Missing required parameters

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestParameterValidation -v
```

**Expected Result**: ⚠️ First test FAILS (this proves the bug exists)
```
test_invalid_json_in_tool_arguments FAILED
test_missing_required_parameters PASSED
```

This test failure demonstrates the JSON parsing vulnerability!

---

### Test Suite 7: Edge Cases (3 tests)

**What it tests**:
- Empty message history
- Very long conversation histories
- Tool returning None

**Run**:
```bash
pytest tests_comprehensive_foodbot.py::TestEdgeCases -v
```

**Expected Result**: ✅ All 3 pass (defensive code handles these)

---

## Test Interpretation Guide

### Understanding Test Failures

If a test fails, the output will show:

```
FAILED tests_comprehensive_foodbot.py::TestToolCallExecution::test_tool_call_execution_failure
_____ TestToolCallExecution.test_tool_call_execution_failure _____

AssertionError: assert None == "expected_value"
```

**What this means**:
- The test expected a specific value
- The actual code returned something different
- This indicates a bug in the implementation

### Reading the Assertion Messages

```python
# Test code
assert mock_tool_response.call_count == 5

# If it fails:
# AssertionError: assert 3 == 5
# This means only 3 tools executed instead of 5
```

### Checking Mock Call Arguments

```python
# After tool execution
mock_tool_response.assert_called_once()
args, kwargs = mock_tool_response.call_args

# Verify specific arguments were passed
assert kwargs["fitness_goal"] == "weight_loss"
assert kwargs["user"] == mock_user
```

---

## Integration Testing (Manual)

### Setup Test User

```python
# Django shell
python manage.py shell

from api.models.user import User
from api.services.ai.orchestrator import FoodBotAIHandler

# Get or create test user
user, created = User.objects.get_or_create(
    phone="1234567890",
    defaults={"name": "Test User"}
)

print(f"User: {user}")
print(f"ID: {user.id}")
```

### Test Handler Initialization

```python
# Should complete without errors
handler = FoodBotAIHandler(user=user)

print(f"Model: {handler.model}")
print(f"Tools registered: {len(handler.tool_functions)}")
print(f"Essential tools: {handler.essential_tools}")
```

### Expected Output

```
Model: gpt-5-nano
Tools registered: 17
Essential tools: ['generate_meal_recommendations', 'place_order', 'contact_support']
```

### Test Message History

```python
history = handler.get_conversation_history()
print(f"Messages in history: {len(history)}")
for i, msg in enumerate(history):
    print(f"{i}: {msg['role']} - {msg['content'][:50]}...")
```

### Expected Pattern

```
0: system - You are a WhatsApp food bot...
1: user - [Last user message]
2: assistant - [Last bot response]
...
```

---

## Performance Testing

### Measure Response Time

```python
import time
from api.services.ai.orchestrator import FoodBotAIHandler

user = User.objects.first()

# Warm up
handler = FoodBotAIHandler(user=user)

# Measure
start = time.time()
# Note: This requires actual OpenAI API call (will fail with mock)
# result = handler.process_message()
elapsed = time.time() - start

print(f"Response time: {elapsed:.2f}s")
# Target: < 3 seconds
```

### Check Token Usage

From the print statements in `process_message()`:

```
LLM usage: CompletionUsage(
    completion_tokens=42,
    prompt_tokens=523,
    total_tokens=565
)
```

**Analysis**:
- Prompt tokens: Input size (too high? Consider embedding filter)
- Completion tokens: Output size
- Total: Should be < 2000 for quality responses

---

## Debugging Failed Tests

### Step 1: Run Single Test in Verbose Mode

```bash
pytest tests_comprehensive_foodbot.py::TestToolCallExecution::test_tool_call_execution_success -vv -s
```

### Step 2: Add Debugging Print Statements

```python
# In test file, add prints to understand mock behavior
def test_tool_call_execution_success(...):
    # ...

    result = handler.process_message()

    print(f"Tool called: {mock_tool_response.called}")
    print(f"Call count: {mock_tool_response.call_count}")
    print(f"Call args: {mock_tool_response.call_args}")

    mock_tool_response.assert_called_once()
```

### Step 3: Check Mock Setup

```python
# Verify mocks are configured correctly
print(f"Mock client: {mock_client}")
print(f"Mock response: {mock_response}")
print(f"Tool functions: {handler.tool_functions.keys()}")
```

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'api'`

**Cause**: Running pytest from wrong directory

**Solution**:
```bash
cd /Users/developer/help/foodie_robot_backend
pytest tests_comprehensive_foodbot.py -v
```

### Issue: `ImportError: cannot import name 'FoodBotAIHandler'`

**Cause**: Django not initialized

**Solution**:
```bash
# Create conftest.py in root
cat > conftest.py << 'EOF'
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodie_robot_backend.settings')
django.setup()
EOF

# Then run tests
pytest tests_comprehensive_foodbot.py -v
```

### Issue: `AttributeError: 'NoneType' object has no attribute 'call_args'`

**Cause**: Mock not set up correctly

**Solution**: Check fixture returns correct Mock object:
```python
mock_response = Mock()  # ✅ Creates actual Mock
mock_response = None    # ❌ Will fail
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test-foodbot.yml
name: FoodBot Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-mock

    - name: Run tests
      run: pytest tests_comprehensive_foodbot.py -v --tb=short

    - name: Generate coverage
      run: |
        pip install pytest-cov
        pytest tests_comprehensive_foodbot.py --cov=api.services.ai
```

---

## After Implementing Fixes

Once you implement the 7 critical fixes from `FOODBOT_QUICK_FIXES.md`, run tests again:

```bash
pytest tests_comprehensive_foodbot.py -v

# All 17 tests should PASS
# Including the parameter validation test that previously failed
```

---

## Summary Checklist

- [ ] Clone/review `tests_comprehensive_foodbot.py`
- [ ] Install pytest and pytest-mock
- [ ] Run all tests: `pytest tests_comprehensive_foodbot.py -v`
- [ ] Note which tests fail (these are bugs!)
- [ ] Review `FOODBOT_ANALYSIS_REPORT.md` for severity levels
- [ ] Implement fixes from `FOODBOT_QUICK_FIXES.md` in order
- [ ] Re-run tests after each fix
- [ ] Verify all 17 tests pass
- [ ] Set up CI/CD to run tests automatically

---

## Next: Implementing Fixes

Once familiar with the test suite, proceed to:
1. Read `FOODBOT_ANALYSIS_REPORT.md` for deep context
2. Follow `FOODBOT_QUICK_FIXES.md` step by step
3. Re-run tests after each fix
4. Commit changes with reference to test improvements

