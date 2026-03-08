"""
Output Formatter - Converts ACPX logs into human-readable summaries using GLM
"""
import requests
import json
import os
from typing import Optional

# GLM/ZAI API Configuration
GLM_DEBUG = os.environ.get('GLM_DEBUG', 'False').lower() in ('true', '1', 'yes')
ZAI_API_KEY = os.environ.get('ZAI_API_KEY', '')
ZAI_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"  # ZAI API endpoint
ZAI_MODEL = "glm-4.5"  # Use glm-4.5 for summarization (ZAI API)

# Fallback patterns if GLM API is unavailable
NOISE_PATTERNS = [
    "jsonrpc",
    "session/update",
    "usage_update",
    "invalid params",
    "invalid input",
    "error handling notification",
    "end_turn",
]


class OutputFormatter:
    """Converts raw ACPX output into human-readable summaries"""

    def __init__(self, use_glm=True):
        self.use_glm = use_glm and ZAI_API_KEY
        self.debug_mode = True  # Enable debug logging for GLM
        self.call_count = 0  # Track API calls

    def summarize_output(self, raw_text: str) -> str:
        """
        Convert raw ACPX logs into human-readable summary

        Args:
            raw_text: Raw ACPX output lines

        Returns:
            Human-readable summary (1-3 lines)
        """
        # Try GLM summarization first
        if self.use_glm:
            try:
                return self._glm_summarize(raw_text)
            except Exception as e:
                print(f"GLM API failed: {e}, using pattern filtering")
                return self._pattern_filter(raw_text)
        else:
            # Use pattern-based filtering
            return self._pattern_filter(raw_text)

    def _glm_summarize(self, raw_text: str) -> str:
        """Call GLM API for summarization"""
        prompt = f"""Convert the following AI coding agent logs into a short human-readable progress update.

Remove:
- JSON-RPC blocks
- telemetry logs
- session updates
- invalid params messages
- error handling notifications

Return only useful development progress in 1-3 short lines.

Logs:
{raw_text}

Summary:"""

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
            
            return summary.strip()
        else:
            raise Exception(f"GLM API error: {response.status_code} - {response.text}")

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

            # Skip noise patterns
            if any(pattern in clean for pattern in NOISE_PATTERNS):
                continue

            # Skip [done] markers
            if clean.startswith("[done]"):
                continue

            # Skip tool indicators (keep only action lines)
            if clean.startswith("[tool]") or clean.startswith("[thinking]"):
                continue

            # Extract useful lines based on keywords
            useful_keywords = [
                "creating", "analyzing", "updating", "building",
                "installing", "reading", "writing", "editing",
                "completed", "success", "done", "running",
                "execute", "generating", "added", "added",
                "file", "component", "page", "style",
            ]

            if any(keyword in clean for keyword in useful_keywords):
                # Truncate long lines to keep summaries short
                if len(line) > 80:
                    line = line[:80] + "..."
                useful_lines.append(line.strip())

            # Stop after collecting 3 useful lines
            if len(useful_lines) >= 3:
                break

        # Return collected lines
        if useful_lines:
            return '\n'.join(useful_lines)
        else:
            # Fallback: return last meaningful line
            for line in reversed(lines):
                if line.strip() and not any(p in line.lower() for p in NOISE_PATTERNS):
                    if len(line) > 80:
                        line = line[:80] + "..."
                    return line.strip()
            return "Processing..."

    def test_api(self) -> bool:
        """Test if GLM API is accessible"""
        if not self.use_glm:
            return False

        try:
            test_prompt = "Say 'API working' in 1 word."
            return self._glm_summarize(test_prompt) == "API working"
        except Exception as e:
            print(f"GLM API test failed: {e}")
            return False
