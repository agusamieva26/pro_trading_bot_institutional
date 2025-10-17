import subprocess
import time
import logging
import sys
import threading
import os
import signal
import webbrowser
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
    """Waits a few seconds and opens the dashboard in the browser."""
    time.sleep(5)  # Give Streamlit time to start
    url = "http://localhost:8501"
    try:
        webbrowser.open(url)
        logger.info(f"🌐 Dashboard abierto en el navegador en: {url}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo abrir el navegador automáticamente. Accede manualmente a: {url}. Error: {e}")

def main():
    """
    Starts and monitors the bot and dashboard processes.
    Restarts them if they crash.
    """
    threading.Thread(target=open_dashboard, daemon=True).start()
    procs: Dict[str, subprocess.Popen] = {}
    logger.info("🚀 Starting Process Supervisor v2.0...")

    try:
        while True:
            for name, command in PROCESSES.items():
                # Check if the process is running
                if name not in procs or procs[name].poll() is not None:
                    if name in procs:
                        logger.warning(f"Process '{name}' terminated with code {procs[name].returncode}. Restarting...")
                    else:
                        logger.info(f"Starting process '{name}' for the first time.")

                    # Start the process with flags for graceful shutdown
                    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                    procs[name] = subprocess.Popen(
                        command, 
                        stdout=sys.stdout, 
                        stderr=sys.stderr,
                        creationflags=creationflags
                    )
                    logger.info(f"✅ Process '{name}' started with PID: {procs[name].pid}")

            time.sleep(5) # Check process status more frequently
    except KeyboardInterrupt:
        logger.info("🛑 User interrupt detected. Shutting down all processes gracefully...")
    finally:
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