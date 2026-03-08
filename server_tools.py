"""
Server monitoring tools using psutil
"""
import psutil


def get_cpu_usage():
    """Get CPU usage percentage"""
    return psutil.cpu_percent(interval=1)


def get_memory_usage():
    """Get memory usage information"""
    mem = psutil.virtual_memory()
    return {
        "total_gb": mem.total / (1024**3),
        "used_gb": mem.used / (1024**3),
        "percent": mem.percent,
        "available_gb": mem.available / (1024**3)
    }


def get_disk_usage():
    """Get disk usage information"""
    disk = psutil.disk_usage('/')
    return {
        "total_gb": disk.total / (1024**3),
        "used_gb": disk.used / (1024**3),
        "percent": disk.percent,
        "free_gb": disk.free / (1024**3)
    }


def get_server_status():
    """Get complete server status"""
    cpu = get_cpu_usage()
    memory = get_memory_usage()
    disk = get_disk_usage()

    return f"""🖥️ **Server Status**

**CPU Usage:** {cpu}%

**Memory:**
  Used: {memory['used_gb']:.2f} GB / {memory['total_gb']:.2f} GB
  Usage: {memory['percent']}%

**Disk:**
  Used: {disk['used_gb']:.2f} GB / {disk['total_gb']:.2f} GB
  Usage: {disk['percent']}%
"""
