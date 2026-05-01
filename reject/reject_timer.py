import time
from collections import deque

from debug_log import log_to_system
from reject.reject_output import reject_output_on, reject_output_off


class RejectTimer:
    def __init__(self, gecikme_suresi=1.20):
        self.gecikme_suresi = float(gecikme_suresi)

        self.queue = deque()
        self.total_scheduled = 0
        self.total_fired = 0

    def update_settings(self, gecikme_suresi=None):
        if gecikme_suresi is not None:
            self.gecikme_suresi = float(gecikme_suresi)

    def clear_queue(self):
        self.queue.clear()
        log_to_system(
            "REJECT KUYRUĞU TEMİZLENDİ",
            "INFO",
            save_csv=False,
            show_ui=True
        )

    def schedule(self, source="AI", meta=None):
        now = time.time()

        item = {
            "trigger_time": now + self.gecikme_suresi,
            "source": source,
            "meta": meta or {}
        }

        self.queue.append(item)
        self.total_scheduled += 1

        log_to_system(
            f"REJECT ZAMANLANDI | kaynak={source} | gecikme={self.gecikme_suresi:.2f}s | meta={item['meta']}",
            "INFO",
            save_csv=True,
            show_ui=True
        )
        return True

    def process(self):
        now = time.time()

        while self.queue and self.queue[0]["trigger_time"] <= now:
            item = self.queue.popleft()
            self.total_fired += 1

            reject_output_on(item)
            reject_output_off(item)