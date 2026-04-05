from database import Database
from transaction_engine import TransactionEngine
import os

# -----------------------------------
# HELPER
# -----------------------------------
def fresh_db():
    db = Database()
    db.tables["Booking"] = {}
    return db


# -----------------------------------
# TEST 1: ATOMICITY
# -----------------------------------
def test_atomicity():
    print("\n===== ATOMICITY TEST =====\n")

    db = fresh_db()
    txn_engine = TransactionEngine(db)

    txn = txn_engine.begin()
    print("Txn started:", txn)

    txn_engine.insert(txn, "Booking", "A1", {"BookingID": "A1"})
    print("Inserted A1 (not committed)")
    txn_engine.print_buffer()

    try:
        raise Exception("Failure before commit")
    except:
        txn_engine.rollback(txn)
        print("Rolled back")
        txn_engine.print_buffer()

    print("Final Table:", db.tables["Booking"])

    if "A1" not in db.tables["Booking"]:
        print("\n RESULT: SUCCESS")
    else:
        print("\n RESULT: FAILED")


# -----------------------------------
# TEST 2: ATOMICITY MULTIPLE
# -----------------------------------
def test_atomicity_multiple():
    print("\n===== ATOMICITY MULTIPLE TEST =====\n")

    db = fresh_db()
    txn_engine = TransactionEngine(db)
    success = 0

    for i in range(6):
        txn = txn_engine.begin()
        print(f"\nTxn {i} started")

        try:
            txn_engine.insert(txn, "Booking", f"A{i}", {"BookingID": f"A{i}"})
            txn_engine.print_buffer()

            if i % 2 == 0:
                raise Exception("Fail")

            txn_engine.commit(txn)
            print("Committed")
            success += 1

        except:
            txn_engine.rollback(txn)
            print("Rolled back")

        txn_engine.print_buffer()

    print("\nFinal Table:", db.tables["Booking"])

    if len(db.tables["Booking"]) == success:
        print("\n RESULT: SUCCESS")
    else:
        print("\n RESULT: FAILED")


# -----------------------------------
# TEST 3: CONSISTENCY
# -----------------------------------
def test_consistency():
    print("\n===== CONSISTENCY TEST =====\n")

    db = fresh_db()
    txn_engine = TransactionEngine(db)

    txn1 = txn_engine.begin()
    txn_engine.insert(txn1, "Booking", "C1", {"BookingID": "C1"})
    txn_engine.print_buffer()
    txn_engine.commit(txn1)

    print("Inserted C1")

    txn2 = txn_engine.begin()
    txn_engine.insert(txn2, "Booking", "C1", {"BookingID": "C1_UPDATED"})
    txn_engine.print_buffer()
    txn_engine.commit(txn2)

    print("Updated C1")

    record = db.tables["Booking"].get("C1")
    print("Final Table:", db.tables["Booking"])

    if record and record["BookingID"] == "C1_UPDATED":
        print("\n RESULT: SUCCESS")
    else:
        print("\n RESULT: FAILED")


# -----------------------------------
# TEST 4: DURABILITY CRASH
# -----------------------------------
def test_crash():
    print("\n===== DURABILITY CRASH TEST =====\n")

    db = fresh_db()
    txn_engine = TransactionEngine(db)

    for i in range(3):
        txn = txn_engine.begin()
        txn_engine.insert(txn, "Booking", f"D{i}", {"BookingID": f"D{i}"})
        txn_engine.commit(txn)
        txn_engine.print_buffer()
        print("Committed:", f"D{i}")

    print("Crashing now...")
    os._exit(1)


# -----------------------------------
# TEST 5: DURABILITY RECOVERY
# -----------------------------------
def test_recovery():
    print("\n===== DURABILITY RECOVERY TEST =====\n")

    db = Database()
    txn_engine = TransactionEngine(db)

    txn_engine.recover()
    txn_engine.print_buffer()

    print("Recovered Table:", db.tables["Booking"])

    if len(db.tables["Booking"]) >= 3:
        print("\n RESULT: SUCCESS")
    else:
        print("\n RESULT: FAILED")


# -----------------------------------
# TEST 6: ISOLATION
# -----------------------------------
def test_isolation():
    print("\n===== ISOLATION TEST =====\n")

    db = fresh_db()
    txn_engine = TransactionEngine(db)

    txn1 = txn_engine.begin()
    txn2 = txn_engine.begin()

    txn_engine.insert(txn1, "Booking", "I1", {"BookingID": "I1"})
    print("txn1 inserted I1 (not committed)")
    txn_engine.print_buffer()

    visible = "I1" in db.tables["Booking"]
    print("txn2 sees I1:", visible)

    txn_engine.commit(txn1)
    txn_engine.print_buffer()

    if not visible:
        print("\n RESULT: SUCCESS")
    else:
        print("\n RESULT: FAILED (Dirty Read)")


# -----------------------------------
# MENU
# -----------------------------------
if __name__ == "__main__":
    print("""
1 Atomicity
2 Atomicity Multiple
3 Consistency
4 Crash
5 Recovery
6 Isolation
""")

    c = input()

    if c == "1":
        test_atomicity()
    elif c == "2":
        test_atomicity_multiple()
    elif c == "3":
        test_consistency()
    elif c == "4":
        test_crash()
    elif c == "5":
        test_recovery()
    elif c == "6":
        test_isolation()