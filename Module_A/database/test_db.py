# from database import Database
# import random
# import os


# def test_commit_50():
#     db = Database()

#     for i in range(50):
#         txn = db.begin()
#         db.insert(txn, "Booking", f"C{i}", {"BookingID": f"C{i}"})
#         db.commit(txn)

#     print("Records after commit:", len(db.tables["Booking"]))


# def test_failure_50():
#     db = Database()
#     success, failed = 0, 0

#     for i in range(50):
#         txn = db.begin()

#         try:
#             db.insert(txn, "Booking", f"F{i}", {"BookingID": f"F{i}"})

#             if i % 3 == 0:
#                 raise Exception()

#             db.commit(txn)
#             success += 1

#         except:
#             db.rollback(txn)
#             failed += 1

#     print("Success:", success, "Failed:", failed)
#     print("Records:", len(db.tables["Booking"]))


# def test_crash_50():
#     db = Database()

#     for i in range(50):
#         txn = db.begin()
#         db.insert(txn, "Booking", f"CR{i}", {"BookingID": f"CR{i}"})

#         if random.random() < 0.2:
#             print("CRASH at", i)
#             os._exit(1)

#         db.commit(txn)


# def test_recovery():
#     db = Database()
#     db.recover()
#     print("Recovered records:", len(db.tables["Booking"]))


# if __name__ == "__main__":
#     print("1 commit | 2 failure | 3 crash | 4 recovery")
#     c = input()

#     if c == "1":
#         test_commit_50()
#     elif c == "2":
#         test_failure_50()
#     elif c == "3":
#         test_crash_50()
#     elif c == "4":
#         test_recovery()

from database import Database
from transaction_engine import TransactionEngine
import random
import os


def test_commit_50():
    db = Database()
    txn_engine = TransactionEngine(db)

    for i in range(50):
        txn = txn_engine.begin()
        txn_engine.insert(txn, "Booking", f"C{i}", {"BookingID": f"C{i}"})
        txn_engine.commit(txn)

    print("Records after commit:", len(db.tables["Booking"]))


def test_failure_50():
    db = Database()
    txn_engine = TransactionEngine(db)

    success, failed = 0, 0

    for i in range(50):
        txn = txn_engine.begin()

        try:
            txn_engine.insert(txn, "Booking", f"F{i}", {"BookingID": f"F{i}"})

            if i % 3 == 0:
                raise Exception()

            txn_engine.commit(txn)
            success += 1

        except:
            txn_engine.rollback(txn)
            failed += 1

    print("Success:", success, "Failed:", failed)
    print("Records:", len(db.tables["Booking"]))


def test_crash_50():
    db = Database()
    txn_engine = TransactionEngine(db)

    for i in range(50):
        txn = txn_engine.begin()
        txn_engine.insert(txn, "Booking", f"CR{i}", {"BookingID": f"CR{i}"})

        if random.random() < 0.2:
            print("CRASH at", i)
            os._exit(1)

        txn_engine.commit(txn)


def test_recovery():
    db = Database()
    txn_engine = TransactionEngine(db)

    txn_engine.recover()
    print("Recovered records:", len(db.tables["Booking"]))


if __name__ == "__main__":
    print("1 commit | 2 failure | 3 crash | 4 recovery")
    c = input()

    if c == "1":
        test_commit_50()
    elif c == "2":
        test_failure_50()
    elif c == "3":
        test_crash_50()
    elif c == "4":
        test_recovery()