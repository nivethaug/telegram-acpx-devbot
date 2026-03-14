"""
Claude runner - executes ACPX Claude tasks via subprocess
FINAL VERSION - Preserves streamed logs, prevents overwrite
"""
import subprocess
import os
import time
from config import ACPX_CLAUDE_PATH, WORKSPACE_DIR, MAX_MESSAGE_LENGTH, PROJECT_ROOT
from output_formatter import OutputFormatter


class ClaudeRunner:
    """Runner for ACPX Claude tasks"""

    def __init__(self, use_glm=True):
        self.process = None
        self.is_running = False
        self.formatter = OutputFormatter(use_glm=use_glm)
        self.output_buffer = []
        self.buffer_size = 3  # Send output every 3 lines
        self.last_summary_time = 0
        self.summary_interval = 5  # Minimum seconds between summaries

    def _validate_path(self, project_path: str) -> bool:
        """
        Validate that project path is safe to use.

        Prevents modification of bot source code or system directories.

        Args:
            project_path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        # Convert to absolute path for comparison
        abs_path = os.path.abspath(project_path)
        abs_project_root = os.path.abspath(PROJECT_ROOT)
        abs_workspace = os.path.abspath(WORKSPACE_DIR)

        # Must be within /root/projects
        if not abs_path.startswith(abs_workspace):
            return False

        # Cannot be bot source directory
        if abs_path.startswith(abs_project_root):
            return False

        return True

    def run_task(self, task, update_callback, project_path=None):
        """
        Run a task via ACPX Claude

        Args:
            task: The task description to run
            update_callback: Function to call with output lines
            project_path: Optional project directory (defaults to WORKSPACE_DIR)

        Returns:
            Return code from subprocess
        """
        # Use provided project path or default to WORKSPACE_DIR
        if project_path is None:
            project_path = WORKSPACE_DIR

        # Validate path for safety
        if not self._validate_path(project_path):
            update_callback(f"❌ Error: Invalid project path: {project_path}")
            update_callback("❌ Tasks can only run in /root/projects/ directories")
            return -1

        # Ensure project directory exists
        os.makedirs(project_path, exist_ok=True)

        self.is_running = True

        # NOTE: Task start message is sent by bot.py dev_command handler
        # Do not send duplicate message here to prevent confusion

        # Build command with stdbuf for UNBUFFERED output
        # CRITICAL: Use bufsize=1 for line-buffered real-time streaming
        cmd = ["stdbuf", "-oL", "node", ACPX_CLAUDE_PATH, "claude", "exec", task]

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # CRITICAL: Line-buffered for real-time streaming
                universal_newlines=True
            )

            # Stream output line by line using readline
            while True:
                line = self.process.stdout.readline()
                
                # Process completion detection
                if not line:
                    if self.process.poll() is not None:
                        # Process finished
                        break
                    continue
                
                line = line.rstrip('\n\r')
                
                # Skip empty lines
                if not line:
                    continue

                # CRITICAL FIX #1: Send EVERY log line to Telegram (no filtering)
                # Raw output - no spam filtering, all ACPX activity visible
                update_callback(line)

                # Send when buffer is full
                if len(self.output_buffer) >= self.buffer_size:
                    raw_text = '\n'.join(self.output_buffer)
                    update_callback(raw_text)
                    self.output_buffer.clear()

            # Wait for process to complete
            return_code = self.process.wait()

            # CRITICAL FIX #2: Flush any remaining stdout that wasn't captured
            remaining_stdout = self.process.stdout.read()
            if remaining_stdout:
                for line in remaining_stdout.splitlines():
                    if line.strip():  # Only send non-empty lines
                        update_callback(line)
            
            self.output_buffer.clear()

            # CRITICAL FIX #3: Send completion message as SEPARATE message (NOT edit)
            # This prevents overwriting all streamed logs with "Processing..."
            if return_code == 0 or return_code == -6:
                # Send as NEW reply (not edit) to preserve logs
                # Use reply_text instead of edit_text
                update_callback(f"\n\n✅ Task finished successfully")
            else:
                # Send failure as separate message
                update_callback(f"\n\n⚠️ Task finished with code: {return_code}")

        except Exception as e:
            update_callback(f"❌ Error: {str(e)}")
            return_code = -1

        finally:
            self.is_running = False
            self.process = None

        return return_code

    def _get_last_useful_line(self):
        """Extract last useful line from buffer as fallback"""
        useful_keywords = [
            "creating", "analyzing", "updating", "building",
            "installing", "reading", "writing", "editing",
            "completed", "success", "done"
        ]

        for line in reversed(self.output_buffer):
            if any(keyword in line.lower() for keyword in useful_keywords):
                # Truncate long lines
                if len(line) > 150:
                    line = line[:150] + "..."
                return line.strip()

        # Fallback: last line
        last_line = self.output_buffer[-1] if self.output_buffer else ""
        return last_line[:150] + "..." if len(last_line) > 150 else last_line.strip()

    def stop(self):
        """Stop currently running task"""
        if self.process and self.is_running:
            self.is_running = False
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            return True
        return False
