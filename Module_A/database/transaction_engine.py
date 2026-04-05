import json
import uuid
import os

LOG_FILE = "wal.log"


class TransactionEngine:

    def __init__(self, db):
        self.db = db
        self.txn_buffer = {}
        self.active_txns = {}

    # ---------------- WAL ----------------
    def log(self, record):
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

    # ---------------- TXN ----------------
    def begin(self):
        txn_id = str(uuid.uuid4())
        self.active_txns[txn_id] = []
        self.txn_buffer[txn_id] = {}
        self.log({"type": "START", "txn": txn_id})
        return txn_id

    def commit(self, txn_id):
        for (table, key), value in self.txn_buffer[txn_id].items():
            self.db.apply_change(table, key, value)

        self.log({"type": "COMMIT", "txn": txn_id})

        self.active_txns.pop(txn_id, None)
        self.txn_buffer.pop(txn_id, None)

        self.db.persist()

    def rollback(self, txn_id):
        if txn_id not in self.active_txns:
            return

        for record in reversed(self.active_txns[txn_id]):
            self.db.apply_change(
                record["table"],
                record["key"],
                record["old"]
            )

        self.active_txns.pop(txn_id, None)
        self.txn_buffer.pop(txn_id, None)

        self.db.persist()

    # ---------------- OPS ----------------
    def insert(self, txn_id, table, key, value):
        old = self.db.tables[table].get(key)

        log_record = {
            "type": "UPDATE",
            "txn": txn_id,
            "table": table,
            "key": key,
            "old": old,
            "new": value
        }

        self.log(log_record)
        self.active_txns[txn_id].append(log_record)

        self.txn_buffer[txn_id][(table, key)] = value

    def delete(self, txn_id, table, key):
        old = self.db.tables[table].get(key)

        log_record = {
            "type": "UPDATE",
            "txn": txn_id,
            "table": table,
            "key": key,
            "old": old,
            "new": None
        }

        self.log(log_record)
        self.active_txns[txn_id].append(log_record)

        self.txn_buffer[txn_id][(table, key)] = None

    # ---------------- DEBUG ----------------
    def print_buffer(self):
        print("\n--- TRANSACTION BUFFER ---")
        for txn, changes in self.txn_buffer.items():
            print(f"{txn}: {changes}")
        print("--------------------------\n")

    # ---------------- RECOVERY ----------------
    def recover(self):
        if not os.path.exists(LOG_FILE):
            return

        logs = []
        with open(LOG_FILE, "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        committed = {log["txn"] for log in logs if log["type"] == "COMMIT"}

        # REDO
        for log in logs:
            if log["type"] == "UPDATE" and log["txn"] in committed:
                self.db.apply_change(log["table"], log["key"], log["new"])

        # UNDO
        for log in reversed(logs):
            if log["type"] == "UPDATE" and log["txn"] not in committed:
                self.db.apply_change(log["table"], log["key"], log["old"])

        self.db.persist()