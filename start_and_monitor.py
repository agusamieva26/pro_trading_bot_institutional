import subprocess
import time
import logging
import sys
import threading
import socket
import os
import signal
import webbrowser
from datetime import datetime
from typing import Dict

# Configure logging to see the monitor's output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("Supervisor")

# Commands to run
PROCESSES = {
    # Use sys.executable to ensure the correct Python interpreter from the virtual environment is used.
    "bot": [sys.executable, "-X", "utf8", "-u", "-m", "bot.main"],
    "dashboard": [sys.executable, "-m", "streamlit", "run", "dashboard_modern.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
}

def open_dashboard():
    """Waits for the Streamlit server to be ready, then opens the dashboard."""
    host = "localhost"
    port = 8501
    url = f"http://{host}:{port}"

    logger.info("Waiting for dashboard to become available...")

    for _ in range(30):  # Wait for up to 30 seconds
        try:
            with socket.create_connection((host, port), timeout=1):
                logger.info("Dashboard is ready. Opening in browser...")
                webbrowser.open(url)
                logger.info(f"🌐 Dashboard abierto en el navegador en: {url}")
                return
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(1)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo abrir el navegador automáticamente. Accede manualmente a: {url}. Error: {e}")
            return
    logger.warning(f"⚠️ Dashboard did not start in time. Please access it manually at: {url}")

def main():
    """
    Starts and monitors the bot and dashboard processes.
    Restarts them if they crash.
    """
    threading.Thread(target=open_dashboard, daemon=True).start()
    procs: Dict[str, subprocess.Popen] = {}
    log_files: Dict[str, object] = {}

    # Create a directory for logs if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logger.info("🚀 Starting Process Supervisor v2.0...")

    def get_log_file(name):
        """Creates a new log file with a timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = os.path.join(log_dir, f"{name}-{timestamp}.log")
        logger.info(f"Opening new log file for '{name}': {log_filename}")
        return open(log_filename, "a")

    try:
        while True:
            for name, command in PROCESSES.items():
                # Check if the process is running
                if name not in procs or procs[name].poll() is not None:
                    if name in procs:
                        # Close old log file if process is being restarted
                        if name in log_files and not log_files[name].closed:
                            log_files[name].close()
                        logger.warning(f"Process '{name}' terminated with code {procs[name].returncode}. Restarting...")
                    else:
                        logger.info(f"Starting process '{name}' for the first time.")

                    # Open a new log file for the new process instance
                    log_files[name] = get_log_file(name)
                    log_file_handle = log_files[name]

                    # Start the process with flags for graceful shutdown
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                    procs[name] = subprocess.Popen(
                        command, 
                        stdout=log_file_handle,
                        stderr=log_file_handle,
                        creationflags=creationflags,
                    )
                    logger.info(f"✅ Process '{name}' started with PID: {procs[name].pid}")

            time.sleep(5) # Check process status more frequently
    except KeyboardInterrupt:
        logger.info("🛑 User interrupt detected. Shutting down all processes gracefully...")
    finally:
        # Close all log files
        for name, f in log_files.items():
            logger.info(f"Closing log file for '{name}'...")
            f.close()

        for name, proc in procs.items():
            if proc.poll() is None: # If process is still running
                logger.info(f"Terminating process '{name}' (PID: {proc.pid})...")
                # Send a graceful shutdown signal.
                if sys.platform == "win32":
                    # On Windows, CTRL_BREAK_EVENT is a reliable way to interrupt
                    # a console process group. Using proc.send_signal is preferred.
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    # On Unix, SIGTERM is the standard graceful shutdown signal.
                    proc.terminate() # Sends SIGTERM on Unix
                
                try:
                    # Wait for the process to terminate gracefully.
                    proc.wait(timeout=15)
                    logger.info(f"✅ Process '{name}' terminated gracefully.")
                except subprocess.TimeoutExpired:
                    # If it doesn't respond, force kill it and its children.
                    logger.warning(f"⚠️ Process '{name}' did not terminate in time. Forcing kill...")
                    if sys.platform == "win32":
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        proc.kill() # Sends SIGKILL on Unix
                    logger.info(f"✅ Process '{name}' killed.")
        logger.info("All processes shut down. Exiting.")

if __name__ == "__main__":
    main()