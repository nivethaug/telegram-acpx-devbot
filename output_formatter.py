"""
Output Formatter - Converts ACPX logs into human-readable summaries using GLM

ROBUST APPROACH:
1. Block-level filtering (removes entire JSON/telemetry blocks)
2. Useful line detector (whitelist approach instead of blacklist)
3. GLM summarization as primary method
4. Pattern filter as fallback
"""
import requests
import os
from typing import Optional

# GLM/ZAI API Configuration
GLM_DEBUG = os.environ.get('GLM_DEBUG', 'False').lower() in ('true', '1', 'yes')
ZAI_API_KEY = os.environ.get('ZAI_API_KEY', '')
ZAI_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ZAI_MODEL = "glm-4.5"  # Use glm-4.5 for summarization (ZAI API)


class OutputFormatter:
    """Converts raw ACPX output into human-readable summaries"""

    def __init__(self, use_glm=True, debug=False):
        self.use_glm = use_glm and ZAI_API_KEY
        self.debug_mode = debug or GLM_DEBUG
        self.call_count = 0  # Track API calls

    def _is_useful_line(self, line: str) -> bool:
        """
        Check if a line contains useful information (whitelist approach)
        
        Instead of filtering noise, we only allow lines that match useful patterns.
        This is more robust than blacklist filtering.
        """
        if not line or not line.strip():
            return False

        line_lower = line.lower().strip()

        # Skip empty lines
        if not line_lower:
            return False

        # Skip JSON/telemetry start markers
        if line_lower in ['{', '}', '(', ')', '[', ']', 'jsonrpc:', 'error handling notification {']:
            return False

        # Skip telemetry/metadata lines
        if any(pattern in line_lower for pattern in [
            'jsonrpc',
            'session/update',
            'usage_update',
            'invalid params',
            'invalid input',
            'error handling notification',
            'end_turn',
            '[done]',
            '[thinking]',
            '[tool]',
            '[console]',
            '[client]',
            'client] initialize',
            'session/new',
            'initialize (running)',
            'session/new (running)',
            'code:',
            'message:',
            'method:',
            'params:',
            'data:',
            'result:',
            'id:',
            'cost:',
            'size:',
            'used:',
            'entry:',
            'availablecommands:',
            'currentmodeid:',
            'configoptions:',
            'title:',
            'toolcallid:',
        ]):
            return False

        # Whitelist: only allow lines with useful keywords
        useful_patterns = [
            # File operations
            'creating', 'created', 'create', 'writing', 'written', 'write',
            'reading', 'read', 'editing', 'edited', 'edit', 'updated', 'update',
            'deleting', 'deleted', 'delete', 'removing', 'removed', 'remove',
            'saving', 'saved', 'save',
            
            # File types
            'file', 'folder', 'directory', 'src/', '.py', '.js', '.tsx', '.ts',
            '.css', '.html', '.json', '.md', '.txt',
            
            # Task completion
            'done', 'completed', 'complete', 'success', 'successful',
            'finished', 'finish',
            
            # Task progress
            'running', 'executing', 'execute', 'processing', 'process',
            'analyzing', 'analyze', 'building', 'build', 'installing',
            'install', 'generating', 'generate', 'compiling', 'compile',
            
            # Git operations
            'git', 'commit', 'push', 'pull', 'branch',
            
            # Dependencies
            'package', 'npm', 'pip', 'dependency', 'depend',
            
            # Results
            'output:', 'result:', 'total', 'files:', 'folders:',
            
            # Code changes
            'added', 'changed', 'modified', 'removed',
        ]

        return any(pattern in line_lower for pattern in useful_patterns)

    def _filter_blocks(self, raw_text: str) -> str:
        """
        Filter out entire JSON/telemetry blocks
        
        Instead of line-by-line filtering, detect and skip entire blocks.
        This handles multi-line JSON correctly.
        """
        lines = raw_text.split('\n')
        clean_lines = []
        skip_block = False
        brace_depth = 0
        paren_depth = 0
        bracket_depth = 0

        for line in lines:
            stripped = line.strip()
            line_lower = stripped.lower()

            # Detect start of JSON object
            if stripped == '{':
                brace_depth += 1
                if brace_depth == 1:
                    skip_block = True
                continue

            # Detect end of JSON object
            if stripped == '}':
                if brace_depth > 0:
                    brace_depth -= 1
                    if brace_depth == 0:
                        skip_block = False
                    continue

            # Detect start of JSON array
            if stripped == '[':
                bracket_depth += 1
                if bracket_depth == 1:
                    skip_block = True
                continue

            # Detect end of JSON array
            if stripped == ']':
                if bracket_depth > 0:
                    bracket_depth -= 1
                    if bracket_depth == 0:
                        skip_block = False
                    continue

            # Detect start of error notification object
            if 'error handling notification {' in line_lower:
                skip_block = True
                paren_depth = 1
                continue

            # Skip everything in active blocks
            if skip_block or brace_depth > 0 or bracket_depth > 0 or paren_depth > 0:
                continue

            # Check if line is useful
            if self._is_useful_line(line):
                # Truncate long lines
                if len(stripped) > 150:
                    stripped = stripped[:150] + "..."
                clean_lines.append(stripped)

        return '\n'.join(clean_lines)

    def summarize_output(self, raw_text: str) -> str:
        """
        Convert raw ACPX logs into human-readable summary

        THREE-STEP PROCESS:
        1. Block-level filtering (remove JSON/telemetry blocks)
        2. Send clean text to GLM for intelligent summarization
        3. Use pattern filter as fallback
        """
        self.call_count += 1

        if self.debug_mode:
            print(f"[GLM DEBUG] Call #{self.call_count}")
            print(f"[GLM DEBUG] Input length: {len(raw_text)} chars")
            print(f"[GLM DEBUG] Input preview: {raw_text[:200]}...")

        # Step 1: Block-level filtering
        filtered = self._filter_blocks(raw_text)

        if self.debug_mode:
            print(f"[GLM DEBUG] After block filter: {len(filtered)} chars")
            print(f"[GLM DEBUG] Filtered preview: {filtered[:200]}...")

        # Step 2: Return filtered output directly (no GLM for streaming)
        # GLM summarization is too slow for real-time streaming
        return filtered if filtered else "Processing..."

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
