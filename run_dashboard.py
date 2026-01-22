"""Launch the modern dashboard to control the bot."""
import sys
import os
import socket
import atexit

# Single instance check using socket binding
LOCK_PORT = 47823  # Arbitrary port for single instance lock

_lock_socket = None

def acquire_single_instance_lock():
    """Ensure only one instance of the dashboard is running."""
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', LOCK_PORT))
        _lock_socket.listen(1)
        return True
    except socket.error:
        return False

def release_lock():
    """Release the single instance lock."""
    global _lock_socket
    if _lock_socket:
        try:
            _lock_socket.close()
        except Exception:
            pass

# Register cleanup
atexit.register(release_lock)

if __name__ == "__main__":
    # Check for existing instance
    if not acquire_single_instance_lock():
        # Try to show a message to the user
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showwarning(
                "Already Running",
                "LinkedIn Auto Job Applier is already running!\n\n"
                "Check your taskbar for the existing window."
            )
            root.destroy()
        except Exception:
            print("ERROR: Dashboard is already running in another window!")
        sys.exit(1)
    
    # Import and run dashboard
    from modules.dashboard.dashboard import run_dashboard
    import runAiBot
    run_dashboard(runAiBot)
