import time
from collections import deque

from debug_log import log_to_system
from reject.reject_output import reject_output_on, reject_output_off


class RejectTimer:
    def __init__(self, delay_seconds=1.20, pulse_seconds=0.15, cooldown_seconds=0.70):
        self.delay_seconds = float(delay_seconds)
        self.pulse_seconds = float(pulse_seconds)
        self.cooldown_seconds = float(cooldown_seconds)

        self.queue = deque()
        self.last_schedule_time = 0.0
        self.total_scheduled = 0
        self.total_fired = 0

    def update_settings(self, delay_seconds=None, pulse_seconds=None, cooldown_seconds=None):
        if delay_seconds is not None:
            self.delay_seconds = float(delay_seconds)
        if pulse_seconds is not None:
            self.pulse_seconds = float(pulse_seconds)
        if cooldown_seconds is not None:
            self.cooldown_seconds = float(cooldown_seconds)

    def clear_queue(self):
        self.queue.clear()
        log_to_system(
            "REJECT QUEUE CLEARED",
            "INFO",
            save_csv=False,
            show_ui=True
        )

    def schedule(self, source="AI", meta=None):
        now = time.time()

        if (now - self.last_schedule_time) < self.cooldown_seconds:
            return False

        item = {
            "trigger_time": now + self.delay_seconds,
            "pulse_seconds": self.pulse_seconds,
            "source": source,
            "meta": meta or {}
        }

        self.queue.append(item)
        self.last_schedule_time = now
        self.total_scheduled += 1

        log_to_system(
            f"REJECT SCHEDULED | source={source} | delay={self.delay_seconds:.2f}s | pulse={self.pulse_seconds:.2f}s | meta={item['meta']}",
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
            time.sleep(float(item["pulse_seconds"]))
            reject_output_off(item)