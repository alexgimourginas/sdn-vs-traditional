import heapq
import threading
import time


class Scheduler:
    """Discrete-event scheduler with wall-clock acceleration.

    Events are (sim_time, seq, callback, args).  The run loop sleeps the
    appropriate real amount of time between events based on `time_scale`:
        real_sleep = sim_delta / time_scale
    time_scale=100 means 1 simulated second passes in 10 ms of real time.
    time_scale=1   means real-time (1 sim-second == 1 real second).
    """

    def __init__(self, time_scale: float = 100.0):
        self._heap: list = []
        self._seq = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.time_scale = time_scale
        self.sim_time: float = 0.0

    def schedule(self, delay: float, callback, *args):
        """Schedule callback(*args) to fire after `delay` simulated seconds."""
        fire_at = self.sim_time + delay
        with self._lock:
            heapq.heappush(self._heap, (fire_at, self._seq, callback, args))
            self._seq += 1

    def schedule_at(self, sim_time: float, callback, *args):
        with self._lock:
            heapq.heappush(self._heap, (sim_time, self._seq, callback, args))
            self._seq += 1

    def run(self, until: float):
        """Run the event loop until simulated time `until`."""
        self._stop.clear()
        real_start = time.perf_counter()
        sim_start = self.sim_time

        while not self._stop.is_set():
            with self._lock:
                if not self._heap:
                                                                
                    self.sim_time = until
                    break
                fire_at, seq, callback, args = self._heap[0]

            if fire_at > until:
                self.sim_time = until
                break

                                                                     
            sim_elapsed = fire_at - sim_start
            real_elapsed = time.perf_counter() - real_start
            target_real = sim_elapsed / self.time_scale
            sleep_for = target_real - real_elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

            with self._lock:
                heapq.heappop(self._heap)

            self.sim_time = fire_at
            try:
                callback(*args)
            except Exception as e:
                print(f"[Scheduler] Error in event at t={fire_at:.4f}: {e}")

    def stop(self):
        self._stop.set()

    def reset(self):
        with self._lock:
            self._heap.clear()
            self._seq = 0
        self.sim_time = 0.0
        self._stop.clear()
