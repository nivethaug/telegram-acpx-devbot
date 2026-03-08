"""
Claude runner - executes ACPX Claude tasks via subprocess
"""
import subprocess
import os
from config import ACPX_CLAUDE_PATH, WORKSPACE_DIR, MAX_MESSAGE_LENGTH


class ClaudeRunner:
    """Runner for ACPX Claude tasks"""

    def __init__(self):
        self.process = None
        self.is_running = False

    def run_task(self, task, update_callback):
        """
        Run a task via ACPX Claude

        Args:
            task: The task description to run
            update_callback: Function to call with output lines
        """
        self.is_running = True

        # Ensure workspace directory exists
        os.makedirs(WORKSPACE_DIR, exist_ok=True)

        # Build command with stdbuf for unbuffered output
        cmd = ["stdbuf", "-oL", "node", ACPX_CLAUDE_PATH, "claude", "exec", task]

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=WORKSPACE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Stream output line by line using readline
            for line in iter(self.process.stdout.readline, ""):
                if not self.is_running:
                    self.process.terminate()
                    break

                line = line.rstrip('\n\r')
                if line:  # Only send non-empty lines
                    # Truncate if too long
                    if len(line) > MAX_MESSAGE_LENGTH:
                        line = line[:MAX_MESSAGE_LENGTH] + "..."

                    update_callback(line)

            # Wait for process to complete
            return_code = self.process.wait()

        except Exception as e:
            update_callback(f"❌ Error: {str(e)}")
            return_code = -1

        finally:
            self.is_running = False
            self.process = None

        return return_code

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
