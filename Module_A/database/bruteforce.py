class BruteForceDB:
    def __init__(self):
        # Store (key, value) pairs for fair comparison with other structures
        self.data = []

    def insert(self, key, value=None):
        # Keep behavior compatible with older code that only inserted keys
        if value is None:
            value = key
        self.data.append((key, value))

    def search(self, key):
        for k, v in self.data:
            if k == key:
                return v
        return None

    def delete(self, key):
        for i, (k, v) in enumerate(self.data):
            if k == key:
                self.data.pop(i)
                return

    def range_query(self, start, end):
        return [(k, v) for k, v in self.data if start <= k <= end]
