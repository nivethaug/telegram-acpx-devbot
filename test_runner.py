"""
Test script for ACPX Claude streaming
Verifies that subprocess stdout streaming works correctly with stdbuf
"""
import subprocess
import os
import time
from config import ACPX_CLAUDE_PATH, WORKSPACE_DIR


def run_acpx_task(task, workspace_dir):
    """
    Run ACPX Claude task with streaming output
    
    Args:
        task: The task description
        workspace_dir: Directory to run in
    """
    print(f"\n{'='*60}")
    print(f"TASK: {task}")
    print(f"{'='*60}")
    
    # Ensure workspace exists
    os.makedirs(workspace_dir, exist_ok=True)
    
    # Build command with stdbuf for unbuffered output
    cmd = ["stdbuf", "-oL", "node", ACPX_CLAUDE_PATH, "claude", "exec", task]
    
    print(f"\n🔧 Command: {' '.join(cmd)}")
    print(f"📁 Workspace: {workspace_dir}")
    print(f"\n📡 Starting subprocess...\n")
    
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output line-by-line with timestamps
        print("📡 STREAMING OUTPUT:\n")
        for line in iter(process.stdout.readline, ""):
            elapsed = time.time() - start_time
            print(f"[{elapsed:.2f}s] STREAM: {line.rstrip()}")
        
        # Wait for process to complete
        return_code = process.wait()
        elapsed = time.time() - start_time
        
        print(f"\n✅ Process completed")
        print(f"⏱️  Total time: {elapsed:.2f}s")
        print(f"🔢 Return code: {return_code}")
        
        return return_code
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return -1


def verify_workspace(workspace_dir):
    """List files in workspace to verify ACPX operations"""
    print(f"\n{'='*60}")
    print(f"VERIFYING WORKSPACE: {workspace_dir}")
    print(f"{'='*60}\n")
    
    try:
        files = os.listdir(workspace_dir)
        if files:
            print(f"📁 Found {len(files)} file(s):")
            for f in sorted(files):
                file_path = os.path.join(workspace_dir, f)
                stat = os.stat(file_path)
                size_kb = stat.st_size / 1024
                print(f"  • {f} ({size_kb:.2f} KB)")
        else:
            print("📁 Workspace is empty")
    except Exception as e:
        print(f"❌ Error listing workspace: {str(e)}")


def main():
    """Run multiple ACPX streaming tests"""
    print("\n" + "="*60)
    print("ACPX STREAMING TEST SUITE")
    print("="*60)
    
    # Test 1: List files
    print("\n\n🧪 TEST 1: List files in workspace")
    print("-" * 60)
    run_acpx_task("list all files in workspace", WORKSPACE_DIR)
    
    # Test 2: Create file
    print("\n\n🧪 TEST 2: Create file streaming_test.md")
    print("-" * 60)
    run_acpx_task('create a file called streaming_test.md with content "Streaming test works!"', WORKSPACE_DIR)
    
    # Test 3: Read file
    print("\n\n🧪 TEST 3: Read file streaming_test.md")
    print("-" * 60)
    run_acpx_task("read the file streaming_test.md", WORKSPACE_DIR)
    
    # Verify workspace
    verify_workspace(WORKSPACE_DIR)
    
    # Summary
    print(f"\n{'='*60}")
    print("✅ TEST SUITE COMPLETED")
    print(f"{'='*60}")
    print("\n📋 Summary:")
    print("  • Test 1: List files")
    print("  • Test 2: Create file")
    print("  • Test 3: Read file")
    print("  • Workspace verification: Done")
    print("\n✨ If all lines appeared with timestamps, streaming is working!")


if __name__ == "__main__":
    main()
