# CS 432 – Databases | Track 1 | Assignment 2
## ShuttleGo – Shuttle Management and Booking System

**Course:** CS 432 – Databases | Semester II (2025–2026)  
**Instructor:** Dr. Yogesh K. Meena  
**Institution:** Indian Institute of Technology, Gandhinagar  

### Team Members:
| Name | Roll No. |
| :--- | :--- |
| Niyati Siju | 23110312 |
| K R Tanvi | 23110149 |
| Makkena Lakshmi Manasa | 23110193 |
| Aeshaa Nehal Shah | 23110018 |
| Suhani | 24110358 |

**Video Demo (Module A):** [Watch here](https://iitgnacin-my.sharepoint.com/:v:/g/personal/23110312_iitgn_ac_in/IQA7oXDkT-AuQI-TG58IFU2jAUJTH7oVLLXuJiZf0O1WBD0?e=7zOhbg) 
**Video Demo (Module B):** [Watch here](https://iitgnacin-my.sharepoint.com/:v:/g/personal/23110312_iitgn_ac_in/IQA7oXDkT-AuQI-TG58IFU2jAUJTH7oVLLXuJiZf0O1WBD0?e=7zOhbg) 
---

## Project Overview
This assignment is divided into two independent modules:
* **Module A** — A lightweight DBMS indexing engine built from scratch using a B+ Tree, benchmarked against a brute-force linear approach.
* **Module B** — A secure local web application with REST APIs, Role-Based Access Control (RBAC), and SQL query optimization for the ShuttleGo system.

---

## Repository Structure
```text
CS432_Track1_Submission/
│
├── Module_A/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── bplustree.py             # B+ Tree implementation
│   │   ├── bruteforce.py            # BruteForceDB baseline
│   │   └── performance_analyzer.py  # Benchmarking utilities
│   ├── report.ipynb                 # Full report with benchmarks & visualizations
│   └── requirements.txt
│
└── Module_B/
    ├── app/                         # API code, UI templates, auth logic
    ├── sql/                         # Database creation scripts
    ├── logs/                        # audit.log
    ├── report.pdf                   # Optimization report
    └── requirements.txtCS 432 – Databases | Track 1 | Assignment 2

ShuttleGo – Shuttle Management and Booking System

Course: CS 432 – Databases | Semester II (2025–2026)

Instructor: Dr. Yogesh K. Meena

Institution: Indian Institute of Technology, Gandhinagar

Team Members:

NameRoll No.Niyati Siju23110312K R Tanvi23110149Makkena Lakshmi Manasa23110193Aeshaa Nehal Shah23110018Suhani24110358Video Demo (Module A): Watch here

Project Overview

This assignment is divided into two independent modules:


Module A — A lightweight DBMS indexing engine built from scratch using a B+ Tree, benchmarked against a brute-force linear approach.

Module B — A secure local web application with REST APIs, Role-Based Access Control (RBAC), and SQL query optimization for the ShuttleGo system.

Repository Structure

CS432_Track1_Submission/

│

├── Module_A/

│   ├── database/

│   │   ├── __init__.py

│   │   ├── bplustree.py          # B+ Tree implementation

│   │   ├── bruteforce.py         # BruteForceDB baseline

│   │   └── performance_analyzer.py  # Benchmarking utilities

│   ├── report.ipynb              # Full report with benchmarks & visualizations

│   └── requirements.txt

│

└── Module_B/

    ├── app/                      # API code, UI templates, auth logic

    ├── sql/                      # Database creation scripts

    ├── logs/                     # audit.log

    ├── report.pdf                # Optimization report

    └── requirements.txt

Module A – Lightweight DBMS with B+ Tree Index

Overview

Module A implements a B+ Tree-based indexing engine and compares it against a BruteForceDB (linear list) approach. Performance is measured across insertion, search, deletion, range queries, and memory usage for dataset sizes from 1,000 to 100,000 elements.


File Descriptions

FileDescriptiondatabase/bplustree.pyFull B+ Tree implementation with insert, delete, search, range query, update, and Graphviz visualizationdatabase/bruteforce.pyBaseline BruteForceDB using a Python list for comparisondatabase/performance_analyzer.pyPerformanceAnalyzer class for timing and deep memory measurementreport.ipynbJupyter notebook with implementation walkthrough, benchmarking plots, tree visualizations, and conclusionsrequirements.txtPython dependenciesSetup & Installation

# Clone the repository

git clone https://github.com/niyatiiii28/CS432_Track1_submission

cd CS432_Track1_submission/Module_A


# Install dependencies

pip install -r requirements.txt


# Launch the notebook

jupyter notebook report.ipynb

Dependencies:


matplotlib

numpy

psutil

graphviz

jupyter

pandas

Note: Graphviz must also be installed on your system.


On Ubuntu/Debian: sudo apt install graphviz


On macOS: brew install graphviz


On Windows: Download from graphviz.org

B+ Tree — Implementation Details

The BPlusTree class supports a minimum degree t (default t=3) and implements:

MethodDescriptioninsert(key, value)Inserts a key-value pair; splits nodes automatically when fullsearch(key)Traverses from root to leaf; returns value or Nonedelete(key)Removes key; rebalances via borrowing or mergingrange_query(start, end)Efficiently scans linked leaf nodes for keys in rangeupdate(key, new_value)Locates key in leaf and updates its valueget_all()Returns all key-value pairs in sorted order via leaf traversalvisualize_tree()Returns a Graphviz Digraph object rendering the full treeNode structure:


BPlusTreeNode.keys — sorted list of keys

BPlusTreeNode.children — child pointers (internal nodes only)

BPlusTreeNode.values — associated values (leaf nodes only)

BPlusTreeNode.next — pointer to next leaf node (linked list)

BruteForceDB — Baseline

BruteForceDB stores (key, value) pairs in a plain Python list. All operations run in linear time and serve as a performance baseline.

OperationComplexityInsertO(1)SearchO(n)DeleteO(n)Range QueryO(n)Performance Analysis

Benchmarks were run across dataset sizes: 1,000 | 5,000 | 10,000 | 50,000 | 100,000


Complexity Comparison

OperationB+ TreeBruteForceDBSearchO(log n)O(n)InsertionO(log n)O(1)DeletionO(log n)O(n)Range QueryO(log n + k)O(n)Key Findings

Insertion: BruteForceDB is faster — simple append() vs. B+ Tree's traversal and potential node splits.

Search: B+ Tree significantly outperforms at scale — logarithmic vs. linear time.

Deletion: B+ Tree scales better; BruteForceDB requires full linear scan per delete.

Range Query: B+ Tree excels due to linked leaf nodes — no repeated root traversals.

Memory: B+ Tree uses ~2× more memory than BruteForceDB due to node pointers and structural overhead.

Sample Memory Usage

Dataset SizeB+ Tree (bytes)BruteForce (bytes)1,000273,880150,4195,0001,287,645707,02410,0002,569,7831,404,70650,00012,746,3976,999,400100,00025,479,14813,900,583Tree Visualization

The visualize_tree() method uses graphviz.Digraph to render:


Internal nodes in light blue

Leaf nodes in light green

Leaf linkage as dashed green edges (representing the linked list)

Run cell 24 in report.ipynb to generate a live visualization, or view the exported bptree.png.

Module B – Local API Development, RBAC & Database Optimization

(Coming soon — see the Module_B folder)

Module B delivers a fully functional web application for the ShuttleGo system with:


Local database setup for shuttle management tables

Secure REST APIs with session-based authentication

Role-Based Access Control (Admin vs. Regular User)

Member portfolio UI

SQL indexing and query profiling

Submission Notes

Deadline: 6:00 PM, 22 March 2026

GitHub Repository: CS432_Track1_submission (private)

Module A video demo linked above

Module B video demo link included in the Module B report

