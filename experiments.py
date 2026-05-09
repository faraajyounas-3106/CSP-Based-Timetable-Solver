
import os
import time
import tempfile

from generator  import InstanceGenerator
from timetable  import build_timetabling_csp
from algorithms import backtrack, forward_checking, mac, min_conflicts
from heuristics import (get_var_heuristic, get_val_heuristic)
from metrics    import Metrics

def _run_one(input_dir, algo_fn, var_h="none", val_h="none",
             max_steps=5000, timeout=30):
  
    import threading

    result_holder = [None]

    def _worker():
        try:
            csp, meta = build_timetabling_csp(input_dir)
        except Exception as e:
            result_holder[0] = {"success": False, "assignments": 0, "backtracks": 0,
                                "checks": 0, "time": 0.0, "error": str(e)}
            return

        var_heuristic = get_var_heuristic(var_h)
        val_heuristic = get_val_heuristic(val_h)
        m = Metrics()

        try:
            if algo_fn.__name__ == "min_conflicts":
                assignment, m = algo_fn(csp, max_steps=max_steps, metrics=m)
            else:
                assignment, m = algo_fn(csp, var_heuristic, val_heuristic, metrics=m)
        except Exception as e:
            result_holder[0] = {"success": False, "assignments": 0, "backtracks": 0,
                                "checks": 0, "time": 0.0, "error": str(e)}
            return

        n_courses = len(csp.variables)
        scheduled = len(assignment) if assignment else 0
        result_holder[0] = {
            "success":     assignment is not None and scheduled == n_courses,
            "assignments": m.assignments,
            "backtracks":  m.backtracks,
            "checks":      m.constraint_checks,
            "time":        m.elapsed,
        }

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if result_holder[0] is None:
        # Timed out
        return {"success": False, "assignments": 0, "backtracks": 0,
                "checks": 0, "time": timeout, "error": "TIMEOUT"}
    return result_holder[0]


def _generate_and_run(n_courses, n_rooms, n_slots, density, tightness,
                      algo_fn, var_h, val_h, n_runs=5, max_steps=5000):
    results = []
    for seed in range(n_runs):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = InstanceGenerator(
                n_courses=n_courses, n_rooms=n_rooms, n_slots=n_slots,
                density=density, tightness=tightness, seed=seed * 42 + 1
            )
            gen.generate(tmpdir)
            r = _run_one(tmpdir, algo_fn, var_h, val_h, max_steps=max_steps)
            results.append(r)

    success_rate   = sum(1 for r in results if r["success"]) / n_runs * 100
    avg_time       = sum(r["time"]        for r in results) / n_runs
    avg_backtracks = sum(r["backtracks"]  for r in results) / n_runs
    avg_checks     = sum(r["checks"]      for r in results) / n_runs
    return success_rate, avg_time, avg_backtracks, avg_checks


def _print_table(title, headers, rows):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)
    col_w = max(14, max(len(h) for h in headers) + 2)
    header_line = " | ".join(f"{h:<{col_w}}" for h in headers)
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print(" | ".join(f"{str(v):<{col_w}}" for v in row))
    print("=" * 80)



def experiment1(n_runs=5):
   
    print("\n" + "=" * 80)
    print("EXPERIMENT 1: Algorithm Comparison")
    print("=" * 80)

    configs = [
        (10, 8,  20, 0.3, 0.3),
        (20, 16, 30, 0.5, 0.5),
        (30, 24, 40, 0.5, 0.5),
        (50, 40, 50, 0.7, 0.7),
    ]

    algorithms = [
        ("Backtrack",        backtrack,        "none",       "none"),
        ("Forward Checking", forward_checking, "mrv_degree", "lcv"),
        ("MAC",              mac,              "mrv_degree", "lcv"),
        ("Min-Conflicts",    min_conflicts,    "none",       "none"),
    ]

    for n_courses, n_rooms, n_slots, density, tightness in configs:
        rows = []
        for label, fn, var_h, val_h in algorithms:
            sr, at, ab, ac = _generate_and_run(
                n_courses, n_rooms, n_slots, density, tightness,
                fn, var_h, val_h, n_runs=n_runs, max_steps=5000
            )
            rows.append([
                label,
                f"{sr:.0f}%",
                f"{at:.3f}s",
                f"{ab:.1f}",
                f"{ac:.0f}",
            ])

        title = (f"Size: {n_courses} courses | {n_rooms} rooms | {n_slots} slots "
                 f"| density={density} | tightness={tightness}")
        _print_table(title,
                     ["Algorithm", "Success%", "Avg Time", "Avg Backtracks", "Avg Checks"],
                     rows)

def experiment2(n_runs=5):
 
    print("\n" + "=" * 80)
    print("EXPERIMENT 2: Heuristic Impact")
    print("=" * 80)

    heuristic_configs = [
        ("No Heuristics",        "none",       "none"),
        ("MRV Only",             "mrv",        "none"),
        ("MRV + Degree",         "mrv_degree", "none"),
        ("MRV + Degree + LCV",   "mrv_degree", "lcv"),
    ]

    rows = []
    for label, var_h, val_h in heuristic_configs:
        sr, at, ab, ac = _generate_and_run(
            20, 16, 30, 0.5, 0.5,
            mac, var_h, val_h, n_runs=n_runs, max_steps=5000
        )
        rows.append([label, f"{sr:.0f}%", f"{at:.3f}s", f"{ab:.1f}", f"{ac:.0f}"])

    baseline_bt = None
    baseline_ck = None
    baseline_tm = None
    enhanced_rows = []
    for i, (row, (label, _, _)) in enumerate(zip(rows, heuristic_configs)):
        sr, at, ab, ac = row
        ab_f = float(ab)
        ac_f = float(ac)
        at_f = float(at[:-1])
        if i == 0:
            baseline_bt = ab_f
            baseline_ck = ac_f
            baseline_tm = at_f
            bt_red = "—"
            ck_red = "—"
            tm_red = "—"
        else:
            bt_red = f"{_pct_reduction(baseline_bt, ab_f):.1f}%"
            ck_red = f"{_pct_reduction(baseline_ck, ac_f):.1f}%"
            tm_red = f"{_pct_reduction(baseline_tm, at_f):.1f}%"
        enhanced_rows.append([label, sr, at, ab, ac, bt_red, ck_red, tm_red])

    _print_table(
        "Heuristic Comparison (MAC, 20 courses, 5 runs each)",
        ["Heuristics", "Success%", "Avg Time", "Avg BTs", "Avg Checks",
         "BT Reduc.", "Chk Reduc.", "Time Reduc."],
        enhanced_rows,
    )


def _pct_reduction(baseline, current):
    if baseline == 0:
        return 0.0
    return max(0.0, (baseline - current) / baseline * 100)


def experiment3(n_runs=5):
   
    print("\n" + "=" * 80)
    print("EXPERIMENT 3: Phase Transition (Tightness 0.1 → 0.9)")
    print("=" * 80)

    tightness_values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    rows = []

    for tightness in tightness_values:
        sr, at, ab, ac = _generate_and_run(
            20, 16, 30, 0.5, tightness,
            mac, "mrv_degree", "lcv", n_runs=n_runs, max_steps=5000
        )
        rows.append([
            f"{tightness:.1f}",
            f"{sr:.0f}%",
            f"{at:.3f}s",
            f"{ab:.1f}",
            f"{ac:.0f}",
        ])

    _print_table(
        "Phase Transition: 20 courses, density=0.5, varying tightness",
        ["Tightness", "Success%", "Avg Time", "Avg Backtracks", "Avg Checks"],
        rows,
    )

    # ASCII chart of satisfiability
    print("\n  Satisfiability Rate (ASCII Plot):")
    print("  Tightness : [Satisfiability]")
    for row in rows:
        tval, sr = row[0], row[1]
        pct = int(float(sr.replace("%", "")))
        bar = "#" * (pct // 5)
        print(f"  {tval}       : {bar:<20} {sr}")

def experiment4(n_runs=5):

    print("\n" + "=" * 80)
    print("EXPERIMENT 4: Systematic (MAC) vs Local Search (Min-Conflicts)")
    print("=" * 80)

    configs = [
        (10, 8,  20, 0.3, 0.3, "Small"),
        (20, 16, 30, 0.5, 0.5, "Medium"),
        (30, 24, 40, 0.5, 0.5, "Large"),
        (50, 40, 50, 0.7, 0.7, "XLarge"),
    ]

    rows = []
    for n_courses, n_rooms, n_slots, density, tightness, size_label in configs:
        mac_sr,  mac_t,  mac_bt,  mac_ck  = _generate_and_run(
            n_courses, n_rooms, n_slots, density, tightness,
            mac, "mrv_degree", "lcv", n_runs=n_runs, max_steps=5000
        )
        mc_sr, mc_t, mc_bt, mc_ck = _generate_and_run(
            n_courses, n_rooms, n_slots, density, tightness,
            min_conflicts, "none", "none", n_runs=n_runs, max_steps=10000
        )
        rows.append([
            size_label,
            f"{mac_sr:.0f}%", f"{mac_t:.3f}s", f"{mac_bt:.1f}",
            f"{mc_sr:.0f}%",  f"{mc_t:.3f}s",  f"{mc_bt:.1f}",
        ])

    _print_table(
        "MAC vs Min-Conflicts Comparison",
        ["Size", "MAC-Success", "MAC-Time", "MAC-BTs",
         "MC-Success",  "MC-Time",  "MC-BTs"],
        rows,
    )

    print("\n  Analysis:")
    print("  - MAC (systematic) guarantees completeness but is slower for large instances.")
    print("  - Min-Conflicts is fast but may not find solutions in hard instances.")
    print("  - MAC outperforms Min-Conflicts when tightness and density are high.")
    print("  - Min-Conflicts is competitive on small/medium easy instances.")


def run_experiment(exp_num, n_runs=5):
    dispatch = {
        1: experiment1,
        2: experiment2,
        3: experiment3,
        4: experiment4,
    }
    if exp_num not in dispatch:
        print(f"Unknown experiment number {exp_num}. Choose from 1-4.")
        return
    dispatch[exp_num](n_runs=n_runs)


if __name__ == "__main__":
    for i in range(1, 5):
        run_experiment(i, n_runs=3)
