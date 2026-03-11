"""
Claude runner - executes ACPX Claude tasks via subprocess
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
        self.buffer_size = 20  # Summarize every 20 lines
        self.last_summary_time = 0
        self.summary_interval = 5  # Minimum seconds between summaries

    def _validate_path(self, project_path: str) -> bool:
        """
        Validate that the project path is safe to use.

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

        # Cannot be the bot source directory
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

        # Send start message IMMEDIATELY (before subprocess)
        update_callback(f"🚀 Task Started\n\n```\n{task}\n```")

        # Build command with stdbuf for unbuffered output
        cmd = ["stdbuf", "-oL", "node", ACPX_CLAUDE_PATH, "claude", "exec", task]

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
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

                # DEBUG MODE: Forward all output raw (no filters, no formatter)
                self.output_buffer.append(line)

                # Send when buffer is full
                if len(self.output_buffer) >= self.buffer_size:
                    raw_text = '\n'.join(self.output_buffer)
                    update_callback(raw_text)
                    self.output_buffer.clear()

            # Wait for process to complete
            return_code = self.process.wait()

            # Flush remaining buffer
            if self.output_buffer:
                raw_text = '\n'.join(self.output_buffer)
                try:
                    summary = self.formatter.summarize_output(raw_text)
                    update_callback(summary)
                except Exception as e:
                    update_callback(self._get_last_useful_line())
                self.output_buffer.clear()

        except Exception as e:
            update_callback(f"❌ Error: {str(e)}")
            return_code = -1

        finally:
            self.is_running = False
            self.process = None

        return return_code

    def _get_last_useful_line(self):
        """Extract the last useful line from buffer as fallback"""
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
        """Stop the currently running task"""
        if self.process and self.is_running:
            self.is_running = False
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            return True
        return False
