

import time


class Metrics:

    def __init__(self):
        self.assignments = 0
        self.backtracks = 0
        self.constraint_checks = 0
        self._start_time = None
        self._end_time = None
        self.events = []


    def start(self):
        self._start_time = time.perf_counter()

    def stop(self):
        self._end_time = time.perf_counter()

    @property
    def elapsed(self):
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else time.perf_counter()
        return end - self._start_time

    def record_assign(self, var_name, value):
        self.assignments += 1
        self.events.append(("assign", var_name, value))

    def record_backtrack(self, var_name):
        self.backtracks += 1
        self.events.append(("backtrack", var_name, None))

    def record_prune(self, var_name, value):
        self.events.append(("prune", var_name, value))


    def report(self):
        return {
            "assignments": self.assignments,
            "backtracks": self.backtracks,
            "constraint_checks": self.constraint_checks,
            "elapsed": self.elapsed,
        }

    def print_report(self, n_courses, n_scheduled):
        print("=" * 58)
        print("PERFORMANCE METRICS")
        print("=" * 58)
        print(f"Total Courses Scheduled  : {n_scheduled}/{n_courses}")
        print(f"Variable Assignments     : {self.assignments}")
        print(f"Backtracks               : {self.backtracks}")
        print(f"Constraint Checks        : {self.constraint_checks}")
        print(f"Execution Time           : {self.elapsed:.4f} seconds")
        quality = "All hard constraints satisfied" if n_scheduled == n_courses else "INCOMPLETE — some courses unscheduled"
        print(f"Solution Quality         : {quality}")
        print("=" * 58)
