from database import Database
from transaction_engine import TransactionEngine
import os


# -----------------------------
# TEST 1: NORMAL COMMIT
# -----------------------------
def test_commit():
    print("\n TEST 1: NORMAL COMMIT\n")

    db = Database()
    txn_engine = TransactionEngine(db)

    txn = txn_engine.begin()

    txn_engine.insert(txn, "Booking", "C1", {
        "BookingID": "C1",
        "Passenger": "Alice"
    })

    txn_engine.commit(txn)

    print("Booking Table:", db.tables["Booking"])


# -----------------------------
# TEST 2: TRANSACTION FAILURE
# -----------------------------
def test_transaction_failure():
    print("\n TEST 2: TRANSACTION FAILURE (ROLLBACK)\n")

    db = Database()
    txn_engine = TransactionEngine(db)

    txn = txn_engine.begin()

    try:
        txn_engine.insert(txn, "Booking", "F1", {
            "BookingID": "F1",
            "Passenger": "Bob"
        })

        # force failure
        raise Exception("Simulated Transaction Error")

        txn_engine.commit(txn)

    except Exception as e:
        print("ERROR:", e)
        txn_engine.rollback(txn)

    print("Booking Table after rollback:", db.tables["Booking"])


# -----------------------------
# TEST 3: SYSTEM CRASH
# -----------------------------
def test_crash():
    print("\n TEST 3: SYSTEM CRASH (STEP 1)\n")

    db = Database()
    txn_engine = TransactionEngine(db)

    txn = txn_engine.begin()

    txn_engine.insert(txn, "Booking", "CR1", {
        "BookingID": "CR1",
        "Passenger": "Charlie"
    })

    print(" Simulating crash BEFORE commit...")
    os._exit(1)   # hard crash


def test_recovery():
    print("\n TEST 3: SYSTEM RECOVERY (STEP 2)\n")

    db = Database()
    txn_engine = TransactionEngine(db)

    txn_engine.recover()

    print("Booking Table after recovery:", db.tables["Booking"])


# -----------------------------
# RUN MENU
# -----------------------------
if __name__ == "__main__":
    print("""
Choose test:
1 → Commit
2 → Transaction Failure
3 → Crash (will exit)
4 → Recovery (run after crash)
""")

    choice = input("Enter choice: ")

    if choice == "1":
        test_commit()

    elif choice == "2":
        test_transaction_failure()

    elif choice == "3":
        test_crash()

    elif choice == "4":
        test_recovery()