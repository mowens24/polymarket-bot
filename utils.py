# utils.py - Small helpers

import time


def sleep_with_status(seconds, status="Waiting for next scan..."):
    print(f"{time.strftime('%H:%M:%S')} - {status}")
    time.sleep(seconds)
