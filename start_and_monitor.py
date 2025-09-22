import subprocess
import time
import logging
import sys

# Configure logging to see the monitor's output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("Supervisor")

# Commands to run
PROCESSES = {
    # 🔧 FIX: Add -X utf8 to force UTF-8 encoding on Windows for emoji support
    "bot": ["python", "-X", "utf8", "-u", "-m", "bot.main"],
    "dashboard": ["streamlit", "run", "dashboard_modern.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.enableCORS", "false"]
}

def main():
    """
    Starts and monitors the bot and dashboard processes.
    Restarts them if they crash.
    """
    procs = {}
    logger.info("🚀 Starting process supervisor...")

    while True:
        for name, command in PROCESSES.items():
            # Check if the process is running
            if name not in procs or procs[name].poll() is not None:
                if name in procs:
                    logger.warning(f"Process '{name}' terminated with code {procs[name].returncode}. Restarting...")
                else:
                    logger.info(f"Starting process '{name}' for the first time.")

                # Start the process
                procs[name] = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr)
                logger.info(f"✅ Process '{name}' started with PID: {procs[name].pid}")

        time.sleep(15)

if __name__ == "__main__":
    main()