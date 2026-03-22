import time
import random
import sys

class PerformanceAnalyzer:

    def __init__(self, structure):
        self.structure = structure

    def measure_insert(self, keys):

        start = time.perf_counter()

        for k in keys:
            try:
                self.structure.insert(k, str(k))
            except TypeError:
                self.structure.insert(k)

        end = time.perf_counter()

        return end - start

    def measure_search(self, keys):

        start = time.perf_counter()

        for k in keys:
            self.structure.search(k)

        end = time.perf_counter()

        return end - start

    def measure_delete(self, keys):

        start = time.perf_counter()

        for k in keys:
            try:
                self.structure.delete(k)
            except:
                pass

        end = time.perf_counter()

        return end - start

    def measure_range_query(self, start_key, end_key):

        start = time.perf_counter()

        try:
            self.structure.range_query(start_key, end_key)
        except:
            pass

        end = time.perf_counter()

        return end - start

    def _deep_getsizeof(self, obj):
        """Estimate the deep memory footprint of an object.

        This traverses container objects (lists, dicts, sets, tuples, and
        objects with __dict__), summing up the size of all reachable objects
        while avoiding double-counting shared references.

        Uses an explicit stack to avoid hitting Python's recursion limit for
        deep / linked structures.
        """

        seen = set()
        total_size = 0
        stack = [obj]

        while stack:
            current = stack.pop()
            obj_id = id(current)
            if obj_id in seen:
                continue
            seen.add(obj_id)

            try:
                total_size += sys.getsizeof(current)
            except TypeError:
                continue

            # Expand known container types
            if isinstance(current, dict):
                for k, v in current.items():
                    stack.append(k)
                    stack.append(v)

            elif isinstance(current, (list, tuple, set, frozenset)):
                stack.extend(current)

            elif hasattr(current, "__dict__"):
                stack.append(current.__dict__)

            elif hasattr(current, "__iter__") and not isinstance(current, (str, bytes, bytearray)):
                try:
                    for item in current:
                        stack.append(item)
                except TypeError:
                    pass

        return total_size

    def memory_usage(self):
        """Return an estimate of the memory used by the wrapped data structure."""

        return self._deep_getsizeof(self.structure)