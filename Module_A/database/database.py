# import json
# import os
# import uuid
# from bplustree import BPlusTree

# LOG_FILE = "wal.log"
# DB_FILE = "db_state.json"


# class Database:

#     def __init__(self):
#         self.tables = {
#             "Booking": {},
#             "Trip": {},
#             "Transaction": {}
#         }
#         self.txn_buffer = {}

#         self.index = {
#             table: BPlusTree(t=3)
#             for table in self.tables
#         }

#         self.active_txns = {}
#         self.load()

#     # ---------------- WAL ----------------
#     def log(self, record):
#         with open(LOG_FILE, "a") as f:
#             f.write(json.dumps(record) + "\n")

#     # ---------------- TXN ----------------
#     def begin(self):
#         txn_id = str(uuid.uuid4())
#         self.active_txns[txn_id] = []
#         self.txn_buffer[txn_id] = {}   
#         self.log({"type": "START", "txn": txn_id})
#         return txn_id

#     def commit(self, txn_id):
#     # Apply buffered changes
#         for (table, key), value in self.txn_buffer[txn_id].items():
#             if value is None:
#                 self.tables[table].pop(key, None)
#                 self.index[table].delete(key)
#             else:
#                 self.tables[table][key] = value
#                 self.index[table].insert(key, value)

#         self.log({"type": "COMMIT", "txn": txn_id})

#         self.active_txns.pop(txn_id, None)
#         self.txn_buffer.pop(txn_id, None)   

#         self.persist()

#     def rollback(self, txn_id):
#         if txn_id not in self.active_txns:
#             return

#         for record in reversed(self.active_txns[txn_id]):
#             table = record["table"]
#             key = record["key"]
#             old = record["old"]

#             if old is None:
#                 self.tables[table].pop(key, None)
#                 self.index[table].delete(key)
#             else:
#                 self.tables[table][key] = old
#                 self.index[table].insert(key, old)

#         self.active_txns.pop(txn_id, None)
#         self.txn_buffer.pop(txn_id, None)
#         self.persist()

#     # ---------------- OPS ----------------
#     def insert(self, txn_id, table, key, value):
#         old = self.tables[table].get(key)

#         log_record = {
#             "type": "UPDATE",
#             "txn": txn_id,
#             "table": table,
#             "key": key,
#             "old": old,
#             "new": value
#         }

#         self.log(log_record)
#         self.active_txns[txn_id].append(log_record)

#         self.txn_buffer[txn_id][(table, key)] = value

#     def update(self, txn_id, table, key, value):
#         self.insert(txn_id, table, key, value)

#     def delete(self, txn_id, table, key):
#         old = self.tables[table].get(key)

#         log_record = {
#             "type": "UPDATE",
#             "txn": txn_id,
#             "table": table,
#             "key": key,
#             "old": old,
#             "new": None
#         }

#         self.log(log_record)
#         self.active_txns[txn_id].append(log_record)

#         self.tables[table].pop(key, None)
#         self.index[table].delete(key)

#     # ---------------- PERSIST ----------------
#     def persist(self):
#         with open(DB_FILE, "w") as f:
#             json.dump(self.tables, f, indent=2)

#     def load(self):
#         if os.path.exists(DB_FILE):
#             with open(DB_FILE, "r") as f:
#                 content = f.read().strip()
#                 if content:
#                     self.tables = json.loads(content)

#         # rebuild index safely
#         for table in self.tables:
#             for key, value in self.tables[table].items():
#                 self.index[table].insert(key, value)

#     def log_recovery(self, msg):
#         with open("recovery.log", "a") as f:
#             f.write(msg + "\n")
            
    
#     # ---------------- RECOVERY ----------------
#     def recover(self):
#         import json
#         import os

#         def log_recovery(msg):
#             with open("recovery.log", "a") as f:
#                 f.write(msg + "\n")

#         if not os.path.exists("wal.log"):
#             print("No WAL log found. Fresh start.")
#             return

#         print("\n🔁 STARTING RECOVERY...\n")
#         log_recovery("===== RECOVERY START =====")

#         logs = []

#         # ---------------- SAFE LOAD WAL ----------------
#         try:
#             with open("wal.log", "r") as f:
#                 for line in f:
#                     line = line.strip()
#                     if line:  # skip empty lines
#                         logs.append(json.loads(line))
#         except Exception as e:
#             print("WAL corrupted or empty:", e)
#             return

#         # ---------------- FIND COMMITTED TXNS ----------------
#         committed = set()

#         for log in logs:
#             if log["type"] == "COMMIT":
#                 committed.add(log["txn"])

#         print(f" Committed Transactions: {len(committed)}")
#         log_recovery(f"Committed TXNs: {len(committed)}")

#         # ---------------- REDO PHASE ----------------
#         print("\n REDO PHASE")
#         log_recovery("---- REDO START ----")

#         for log in logs:
#             if log["type"] == "UPDATE" and log["txn"] in committed:
#                 table = log["table"]
#                 key = log["key"]
#                 new = log["new"]

#                 msg = f"REDO -> {log['txn']} | {table} | {key}"
#                 print(msg)
#                 log_recovery(msg)

#                 if new is None:
#                     # delete case
#                     self.tables[table].pop(key, None)
#                 else:
#                     self.tables[table][key] = new

#         log_recovery("---- REDO END ----")

#         # ---------------- UNDO PHASE ----------------
#         print("\n UNDO PHASE")
#         log_recovery("---- UNDO START ----")

#         for log in reversed(logs):
#             if log["type"] == "UPDATE" and log["txn"] not in committed:
#                 table = log["table"]
#                 key = log["key"]
#                 old = log["old"]

#                 msg = f"UNDO -> {log['txn']} | {table} | {key}"
#                 print(msg)
#                 log_recovery(msg)

#                 if old is None:
#                     # means it was an insert → remove it
#                     self.tables[table].pop(key, None)
#                 else:
#                     # restore old value
#                     self.tables[table][key] = old

#         log_recovery("---- UNDO END ----")

#         # ---------------- FINAL SAVE ----------------
#         self.persist()

#         print("\n RECOVERY COMPLETE\n")
#         log_recovery("===== RECOVERY COMPLETE =====\n")

#     def reset_files():
#         open("wal.log", "w").close()
#         open("db_state.json", "w").write("{}")
#     def print_buffer(self):
#         print("\n--- TRANSACTION BUFFER ---")

#         if not hasattr(self, "txn_buffer") or not self.txn_buffer:
#             print("No active transaction buffers")
#         else:
#             for txn, changes in self.txn_buffer.items():
#                 print(f"{txn}: {changes}")

#         print("--------------------------\n")

import json
import os
from bplustree import BPlusTree

DB_FILE = "db_state.json"


class Database:

    def __init__(self):
        self.tables = {
            "Booking": {},
            "Trip": {},
            "Transaction": {}
        }

        self.index = {
            table: BPlusTree(t=3)
            for table in self.tables
        }

        self.load()

    # ---------------- BASIC OPS ----------------
    def apply_change(self, table, key, value):
        if value is None:
            self.tables[table].pop(key, None)
            self.index[table].delete(key)
        else:
            self.tables[table][key] = value
            self.index[table].insert(key, value)

    # ---------------- PERSIST ----------------
    def persist(self):
        with open(DB_FILE, "w") as f:
            json.dump(self.tables, f, indent=2)

    def load(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    self.tables = json.loads(content)

        for table in self.tables:
            for key, value in self.tables[table].items():
                self.index[table].insert(key, value)