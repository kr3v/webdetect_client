from __future__ import annotations

import subprocess
import time
from typing import Callable, List


class Async:
    invoke: Callable[[], subprocess.Popen]
    popen: subprocess.Popen
    next: Async
    started: bool
    finished: bool

    def __init__(self, invoke: Callable[[], subprocess.Popen]):
        self.result = None
        self.invoke = invoke
        self.popen = None
        self.next = None
        self.started = False
        self.finished = False

    def start(self):
        if not self.started:
            self.started = True
            self.popen = self.invoke()
            if self.popen is None:
                self.finished = True

    def is_started(self):
        return self.started

    def is_finished(self):
        if not self.finished and self.popen is not None and self.popen.poll() is not None:
            self.finished = True
        return self.started and self.finished

    def and_then(self, func: Callable[[], subprocess.Popen]) -> Async:
        curr = self
        while curr.next is not None:
            curr = curr.next
        curr.next = Async(func)
        return self


def exec_async(processes: List[Async]):
    while len([x for x in processes if x is not None and not x.finished]) > 0:
        for i in range(0, len(processes)):
            proc = processes[i]

            if proc is None:
                continue

            if not proc.is_started():
                proc.start()

            while proc is not None and proc.is_finished():
                proc = proc.next
                processes[i] = proc
                if proc is not None:
                    proc.start()
        time.sleep(1)
