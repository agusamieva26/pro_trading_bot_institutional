# run.py
import threading
import time
from bot.main import main
from daily_reporter import run_reporter

def run_main():
    main()

def run_scheduler():
    run_reporter()

if __name__ == "__main__":
    t1 = threading.Thread(target=run_main, daemon=True)
    t2 = threading.Thread(target=run_scheduler, daemon=True)

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Bot detenido por el usuario.")