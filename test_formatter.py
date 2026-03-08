"""Test output formatter with and without GLM API"""

from output_formatter import OutputFormatter

# Sample noisy ACPX output
noisy_output = """[done] end_turn
jsonrpc: '2.0'
method: 'session/update'
sessionUpdate: 'usage_update'
message: 'Invalid params'
Invalid input: expected object, received undefined
Invalid input: expected object, received undefined
[thinking] Analyzing React project structure
[tool] Terminal (pending)
[tool] ls -la (completed)
Creating file test_component.jsx
Writing component code
Adding styles
File created successfully
[done] end_turn"""

print("=" * 60)
print("Testing OutputFormatter")
print("=" * 60)

# Test 1: Without GLM (pattern filtering only)
print("\n1. Pattern-based Filtering (GLM disabled)")
print("-" * 60)
formatter_no_glm = OutputFormatter(use_glm=False)
summary = formatter_no_glm.summarize_output(noisy_output)
print("Summary:")
print(summary)

# Test 2: With GLM (will fail gracefully since no API key)
print("\n2. GLM Summarization (will fall back to patterns)")
print("-" * 60)
formatter_with_glm = OutputFormatter(use_glm=True)
summary = formatter_with_glm.summarize_output(noisy_output)
print("Summary:")
print(summary)

# Test 3: API test
print("\n3. API Connectivity Test")
print("-" * 60)
api_working = formatter_with_glm.test_api()
print(f"GLM API accessible: {api_working}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
