import threading
import time
from .services import save_traffic_snapshot
from . import state


def start_traffic_logger():
    def run():
        while True:
            if state.camera_active:
                save_traffic_snapshot()
            time.sleep(10)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()