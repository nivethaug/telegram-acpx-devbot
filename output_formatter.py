"""
Output Formatter - Converts ACPX logs into human-readable summaries using GLM

HYBRID APPROACH:
1. Pre-filter noise (remove JSON-RPC, telemetry, markers)
2. Send clean text to GLM for intelligent summarization
3. Use pattern filter as fallback
"""
import requests
import os
from typing import Optional

# GLM/ZAI API Configuration
GLM_DEBUG = os.environ.get('GLM_DEBUG', 'False').lower() in ('true', '1', 'yes')
ZAI_API_KEY = os.environ.get('ZAI_API_KEY', '')
ZAI_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ZAI_MODEL = "glm-4.5"  # Use glm-4.5 for summarization (ZAI API)

# Noise patterns to filter BEFORE sending to GLM
NOISE_PATTERNS = [
    "jsonrpc",
    "session/update",
    "usage_update",
    "invalid params",
    "invalid input",
    "error handling notification",
    "end_turn",
    "[done]",
    "[thinking]",
    "[tool]",
    "[console]",
    "[client]",
    "client] initialize",
    "session/new",
    "initialize (running)",
    "session/new (running)",
]


class OutputFormatter:
    """Converts raw ACPX output into human-readable summaries"""

    def __init__(self, use_glm=True, debug=False):
        self.use_glm = use_glm and ZAI_API_KEY
        self.debug_mode = debug or GLM_DEBUG
        self.call_count = 0  # Track API calls

    def _pre_filter(self, raw_text: str) -> str:
        """
        Filter out noise BEFORE sending to GLM
        
        Removes JSON-RPC, telemetry, and other non-useful patterns
        Returns clean input for GLM summarization
        """
        lines = raw_text.split('\n')
        clean_lines = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            clean = line.lower()
            
            # Skip noise patterns
            if any(pattern in clean for pattern in NOISE_PATTERNS):
                continue
            
            # Skip [tool], [thinking], [console], [client] markers
            if any(clean.startswith(prefix) for prefix in ["[tool]", "[thinking]", "[console]", "[client]"]):
                continue
            
            clean_lines.append(line.strip())
        
        return '\n'.join(clean_lines)

    def summarize_output(self, raw_text: str) -> str:
        """
        Convert raw ACPX logs into human-readable summary
        
        TWO-STEP PROCESS:
        1. Pre-filter noise (remove JSON-RPC, telemetry, etc.)
        2. Send cleaned text to GLM for intelligent summarization
        3. Use pattern filter as fallback
        """
        self.call_count += 1

        if self.debug_mode:
            print(f"[GLM DEBUG] Call #{self.call_count}")
            print(f"[GLM DEBUG] Input length: {len(raw_text)} chars")
            print(f"[GLM DEBUG] Input preview: {raw_text[:200]}...")

        # Step 1: Pre-filter noise
        if not self.use_glm:
            if self.debug_mode:
                print("[GLM DEBUG] GLM disabled, using pattern filter")
            return self._pattern_filter(raw_text)

        if not raw_text.strip():
            if self.debug_mode:
                print("[GLM DEBUG] Empty input, using pattern filter")
            return self._pattern_filter(raw_text)

        # Step 2: Pre-filter noise, then send to GLM
        pre_filtered = self._pre_filter(raw_text)
        
        if self.debug_mode:
            print(f"[GLM DEBUG] After pre-filter: {len(pre_filtered)} chars")
            print(f"[GLM DEBUG] Pre-filtered preview: {pre_filtered[:200]}...")

        # Step 3: Send pre-filtered text to GLM
        prompt = f"""Summarize this coding activity in 1 short sentence.

{pre_filtered}

Answer:"""

        headers = {
            "Authorization": f"Bearer {ZAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": ZAI_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Low temperature for concise output
            "max_tokens": 100    # Short summaries
        }

        response = requests.post(
            ZAI_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            summary = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if self.debug_mode:
                print(f"[GLM DEBUG] Response: {summary[:100]}")
                print(f"[GLM DEBUG] Summary length: {len(summary)} chars")
            
            # Return summary if non-empty, otherwise fallback to pattern filter
            if summary.strip():
                return summary.strip()
            else:
                if self.debug_mode:
                    print("[GLM DEBUG] Empty response, using pattern filter")
                return self._pattern_filter(raw_text)
        else:
            error_msg = f"GLM API error: {response.status_code} - {response.text[:200]}"
            if self.debug_mode:
                print(f"[GLM DEBUG] {error_msg}")
            raise Exception(error_msg)

    def _pattern_filter(self, raw_text: str) -> str:
        """
        Fallback: Use pattern-based filtering

        Extracts only useful lines based on keyword detection
        Returns top 3 useful lines
        """
        lines = raw_text.split('\n')
        useful_lines = []

        for line in lines:
            clean = line.lower().strip()

            # Skip empty lines
            if not clean:
                continue

            # Skip [done] markers
            if clean.startswith("[done]"):
                continue

            # Extract useful lines based on keywords
            useful_keywords = [
                "creating", "analyzing", "updating", "building",
                "installing", "reading", "writing", "editing",
                "completed", "success", "done", "running",
                "execute", "generating", "added", "installed", "saved"
            ]

            if any(keyword in clean for keyword in useful_keywords):
                # Truncate long lines
                if len(line) > 150:
                    line = line[:150] + "..."
                useful_lines.append(line.strip())

        # Return top 3 useful lines
        if useful_lines:
            return '\n'.join(useful_lines[:3])
        else:
            # Fallback: return last meaningful line
            for line in reversed(lines):
                if line.strip() and not any(p in line.lower() for p in NOISE_PATTERNS):
                    if len(line) > 100:
                        line = line[:100] + "..."
                    return line.strip()
            return "Processing..."

    def test_api(self) -> bool:
        """Test if GLM API is accessible"""
        if not self.use_glm:
            return False

        try:
            test_prompt = "Say hello"
            return self._glm_summarize(test_prompt) == "Hello there!" or "Hi there!"
        except Exception as e:
            print(f"GLM API test failed: {e}")
            return False
