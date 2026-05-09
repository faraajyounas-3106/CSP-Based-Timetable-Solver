## University Course Timetabling using Constraint Satisfaction Problems (CSP)
---

### Overview

This project implements a complete **Constraint Satisfaction Problem (CSP)** solver for the **University Course Timetabling Problem**. It supports multiple systematic search algorithms with inference techniques, variable/value ordering heuristics, arc consistency (AC-3), and a local search method (Min-Conflicts).

The system can:
- Solve real and generated timetabling instances
- Run four standard experiments for performance analysis
- Visualize the solution (grid view) and search process (bonus GUI)

---

### Features Implemented

| Feature                              | Status     | Algorithm / Technique                  |
|--------------------------------------|------------|----------------------------------------|
| Backtracking Search                  | ✅ Complete | Basic backtracking                     |
| Forward Checking                     | ✅ Complete | Backtracking + FC                      |
| Maintaining Arc Consistency (MAC)    | ✅ Complete | Backtracking + AC-3                    |
| Min-Conflicts Local Search           | ✅ Complete | Local search                           |
| Variable Ordering Heuristics         | ✅ Complete | MRV, MRV + Degree                     |
| Value Ordering Heuristics            | ✅ Complete | LCV                                    |
| Experiments 1–4                      | ✅ Complete | Algorithm comparison, heuristics, phase transition, systematic vs local |
| Instance Generator                   | ✅ Complete | Controllable difficulty                |
| Bonus GUI (Search Animation + Grid)  | ✅ Complete | Tkinter + Matplotlib                   |

