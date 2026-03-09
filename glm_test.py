#!/usr/bin/env python3
"""
GLM API Test Script
"""
import requests
import os

api_key = os.environ.get('ZAI_API_KEY', '')
api_url = "https://api.z.ai/api/coding/paas/v4/chat/completions"

print("=" * 60)
print("GLM API Test Script")
print("=" * 60)

print(f"API Key: {'SET' if api_key else 'NOT SET'}")
print(f"Key Length: {len(api_key)} chars")
print(f"API URL: {api_url}")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# Test 1: Simple request
print("\n1. Testing simple request...")
simple_payload = {
    "model": "glm-4.5",
    "messages": [{"role": "user", "content": "Hi"}],
    "temperature": 0.3,
    "max_tokens": 10
}

try:
    resp = requests.post(api_url, headers=headers, json=simple_payload, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response: {content}")
        print(f"Response length: {len(content)} chars")
        if content.strip():
            print("✅ GLM API works for simple requests")
        else:
            print("❌ GLM API returned empty response for simple requests")
    else:
        print(f"Error: {resp.text[:300]}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 2: Summarization request
print("\n2. Testing summarization request...")
summary_payload = {
    "model": "glm-4.5",
    "messages": [
        {
            "role": "user",
            "content": """Convert the following AI coding agent logs into a short human-readable progress update.

Remove:
- JSON-RPC blocks
- telemetry logs
- session updates
- invalid params messages
- error handling notifications

Return only useful development progress in 1-3 short lines.

Logs:
Creating file test_component.jsx
Writing component code
Adding styles
File created successfully

Summary:"""
        }
    ],
    "temperature": 0.3,
    "max_tokens": 20
}

try:
    resp = requests.post(api_url, headers=headers, json=summary_payload, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response: {content}")
        print(f"Response length: {len(content)} chars")
        if content.strip():
            print("✅ GLM API works for summarization")
        else:
            print("❌ GLM API returned empty response for summarization")
    else:
        print(f"Error: {resp.text[:300]}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)