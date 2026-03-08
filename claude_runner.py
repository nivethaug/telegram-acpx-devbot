"""
Claude runner - executes ACPX Claude tasks via subprocess
"""
import subprocess
import os
import time
from config import ACPX_CLAUDE_PATH, WORKSPACE_DIR, MAX_MESSAGE_LENGTH
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

                # Skip empty lines
                if not line:
                    continue

                # Add to buffer for summarization
                self.output_buffer.append(line)

                # Send summary when buffer is full or interval elapsed
                current_time = time.time()
                time_since_last = current_time - self.last_summary_time

                should_summarize = (
                    len(self.output_buffer) >= self.buffer_size or
                    time_since_last >= self.summary_interval
                )

                if should_summarize:
                    # Generate summary using GLM or pattern filtering
                    raw_text = '\n'.join(self.output_buffer)
                    try:
                        summary = self.formatter.summarize_output(raw_text)
                        update_callback(summary)
                    except Exception as e:
                        # Fallback: send last useful line
                        print(f"Summarization failed: {e}")
                        update_callback(self._get_last_useful_line())

                    # Reset buffer
                    self.output_buffer.clear()
                    self.last_summary_time = current_time

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
