import os
import queue
import traceback
from concurrent.futures import ThreadPoolExecutor


class BlockingExecutor:
    def __init__(self, thread_count, cache_size):
        if cache_size <= 0:
            raise ValueError('cache_size must > 0')
        self.finish = False
        self.executor = ThreadPoolExecutor(thread_count, thread_name_prefix='Blocking')
        self.queue = queue.Queue(maxsize=cache_size)
        self.futures = []
        for i in range(thread_count):
            self.futures.append(self.executor.submit(self.call_function))

    def call_function(self):
        # finish之后queue中还有至少一个要处理，
        while not (self.finish and self.queue.empty()):
            try:
                (task, args) = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                task(*args)
            except:
                traceback.print_exc()
                os._exit(1)

    def submit(self, task, *args):
        self.queue.put((task, args))

    def shutdown(self):
        self.finish = True
        self.executor.shutdown()
