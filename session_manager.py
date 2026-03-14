"""
Session Manager for Telegram ACPX Dev Bot
Manages isolated coding sessions with workspace isolation
"""
import uuid
import time
import subprocess
from pathlib import Path

# In-memory session storage
SESSIONS = {}

# Allowed base paths for safety
ALLOWED_BASE_PATHS = [
    Path("/root"),
    Path("/home"),
    Path("/projects"),
    Path("/root/workspaces"),  # NEW: Allow session workspaces
]

WORKSPACES_DIR = Path("/root/workspaces")


def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"sess_{uuid.uuid4().hex[:6]}"


def is_path_allowed(path: str) -> bool:
    """Check if path is within allowed directories"""
    path_obj = Path(path).resolve()

    for base in ALLOWED_BASE_PATHS:
        try:
            path_obj.relative_to(base)
            return True
        except ValueError:
            continue
    return False


def create_session(user_id: int, project_path: str) -> dict:
    """Create a new isolated session"""
    session_id = generate_session_id()

    # Validate path
    if not is_path_allowed(project_path):
        return {
            "error": "Path not allowed",
            "message": "Project path must be within /root, /home, or /projects"
        }

    project_path_obj = Path(project_path)
    if not project_path_obj.exists():
        return {
            "error": "Path not found",
            "message": f"Project directory does not exist: {project_path}"
        }

    # Create workspace
    workspace_path = WORKSPACES_DIR / session_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories (repo will be a symlink, not a directory)
    (workspace_path / "logs").mkdir(exist_ok=True)
    (workspace_path / "context").mkdir(exist_ok=True)
    (workspace_path / "temp").mkdir(exist_ok=True)

    # Create symlink to repo
    repo_link = workspace_path / "repo"
    try:
        # Remove existing link if present
        if repo_link.exists() or repo_link.is_symlink():
            repo_link.unlink()
        # Create symlink to project path
        repo_link.symlink_to(project_path_obj)
    except Exception as e:
        return {
            "error": "Symlink failed",
            "message": f"Failed to create symlink: {e}"
        }

    session = {
        "session_id": session_id,
        "user_id": user_id,
        "workspace": str(workspace_path),
        "repo_path": str(project_path_obj),
        "repo_link": str(repo_link),  # Workspace repo symlink location
        "running": False,
        "process": None,
        "queue": [],
        "created_at": time.time(),
        "last_activity": time.time()
    }

    SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> dict | None:
    """Get session by ID"""
    return SESSIONS.get(session_id)


def get_active_session(user_id: int) -> dict | None:
    """Get active session for user"""
    for sid, sess in SESSIONS.items():
        if sess["user_id"] == user_id and sess["running"]:
            return sess
    return None


def get_session_by_chat_id(chat_id: int) -> dict | None:
    """
    Get most recent session for a chat ID (doesn't require session to be running).

    Args:
        chat_id: Telegram chat ID

    Returns:
        Session dict if found, None otherwise
    """
    # Find all sessions for this chat_id
    chat_sessions = []
    for sid, sess in SESSIONS.items():
        if sess["user_id"] == chat_id:
            chat_sessions.append((sess["created_at"], sess))

    if not chat_sessions:
        return None

    # Sort by creation time (most recent first) and return latest
    chat_sessions.sort(key=lambda x: x[0], reverse=True)
    return chat_sessions[0][1]  # Return session (not timestamp)


def update_session_activity(session_id: str):
    """Update last activity timestamp"""
    if session_id in SESSIONS:
        SESSIONS[session_id]["last_activity"] = time.time()


def set_session_running(session_id: str, running: bool, process=None):
    """Set session running state and attach process"""
    if session_id in SESSIONS:
        SESSIONS[session_id]["running"] = running
        if process:
            SESSIONS[session_id]["process"] = process
        SESSIONS[session_id]["last_activity"] = time.time()


def close_session(session_id: str) -> bool:
    """Close a session and cleanup"""
    if session_id not in SESSIONS:
        return False

    session = SESSIONS[session_id]

    # Terminate process if running
    if session.get("process"):
        try:
            session["process"].terminate()
            session["process"].wait(timeout=5)
        except:
            try:
                session["process"].kill()
            except:
                pass

    # Delete workspace
    workspace_path = Path(session["workspace"])
    if workspace_path.exists():
        import shutil
        shutil.rmtree(workspace_path, ignore_errors=True)

    del SESSIONS[session_id]
    return True


def cleanup_sessions(max_age_hours: int = 24):
    """Clean up stale sessions"""
    current_time = time.time()
    to_remove = []

    for sid, sess in SESSIONS.items():
        age_hours = (current_time - sess["created_at"]) / 3600
        if age_hours > max_age_hours and not sess["running"]:
            to_remove.append(sid)

    for sid in to_remove:
        close_session(sid)

    return len(to_remove)


def list_sessions(user_id: int = None) -> list:
    """List all sessions (or user's sessions)"""
    if user_id:
        return [s for s in SESSIONS.values() if s["user_id"] == user_id]
    return list(SESSIONS.values())
