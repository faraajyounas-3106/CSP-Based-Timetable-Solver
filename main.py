
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from timetable  import build_timetabling_csp, print_solution
from algorithms import get_algorithm, ALGORITHM_LABELS
from heuristics import get_var_heuristic, get_val_heuristic
from metrics    import Metrics
from generator  import InstanceGenerator
from experiments import run_experiment


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI2002 — University Course Timetabling CSP Solver",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # --- Solve mode ---
    parser.add_argument(
        "--input-dir", type=str, default=None,
        help="Directory containing courses.csv, rooms.csv, timeslots.csv, students.csv"
    )
    parser.add_argument(
        "--algorithm", type=str, default="mac",
        choices=["backtrack", "forward_checking", "mac", "min_conflicts"],
        help=(
            "Algorithm to use:\n"
            "  backtrack        - Basic backtracking\n"
            "  forward_checking - Backtracking with forward checking\n"
            "  mac              - MAC (AC-3) backtracking\n"
            "  min_conflicts    - Min-Conflicts local search"
        ),
    )
    parser.add_argument(
        "--var-heuristic", type=str, default="mrv_degree",
        choices=["none", "mrv", "mrv_degree"],
        help="Variable ordering heuristic (default: mrv_degree)",
    )
    parser.add_argument(
        "--val-heuristic", type=str, default="lcv",
        choices=["none", "lcv"],
        help="Value ordering heuristic (default: lcv)",
    )
    parser.add_argument(
        "--max-steps", type=int, default=50000,
        help="Max steps for Min-Conflicts (default: 50000)",
    )

    # --- Generate mode ---
    parser.add_argument(
        "--generate", action="store_true",
        help="Generate a new problem instance",
    )
    parser.add_argument("--courses",    type=int, default=10)
    parser.add_argument("--rooms",      type=int, default=8)
    parser.add_argument("--slots",      type=int, default=20)
    parser.add_argument("--density",    type=float, default=0.3)
    parser.add_argument("--tightness",  type=float, default=0.3)
    parser.add_argument("--seed",       type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="instances/generated/")

    # --- Experiment mode ---
    parser.add_argument(
        "--experiment", type=int, default=None, choices=[1, 2, 3, 4],
        help="Run experiment 1-4",
    )
    parser.add_argument(
        "--runs", type=int, default=5,
        help="Number of runs per configuration in experiments (default: 5)",
    )

    # --- GUI mode ---
    parser.add_argument(
        "--gui", action="store_true",
        help="Launch the GUI visualiser",
    )

    return parser.parse_args()


def solve_instance(args):
    """Load CSP from input_dir and solve using chosen algorithm + heuristics."""
    if not os.path.isdir(args.input_dir):
        print(f"ERROR: Input directory '{args.input_dir}' not found.")
        sys.exit(1)

    print(f"\nLoading instance from: {args.input_dir}")
    try:
        csp, meta = build_timetabling_csp(args.input_dir)
    except Exception as e:
        print(f"ERROR loading CSP: {e}")
        raise

    n_vars = len(csp.variables)
    print(f"Variables: {n_vars} courses")
    total_domain = sum(len(csp.domains[v]) for v in csp.variables)
    print(f"Total domain size (all variables): {total_domain}")

    algo_fn    = get_algorithm(args.algorithm)
    var_h_fn   = get_var_heuristic(args.var_heuristic)
    val_h_fn   = get_val_heuristic(args.val_heuristic)
    algo_label = ALGORITHM_LABELS[args.algorithm]

    # Suffix label with heuristics (min_conflicts doesn't use these)
    if args.algorithm != "min_conflicts":
        h_parts = []
        if args.var_heuristic != "none":
            h_parts.append(args.var_heuristic.upper())
        if args.val_heuristic != "none":
            h_parts.append(args.val_heuristic.upper())
        if h_parts:
            algo_label += " + " + " + ".join(h_parts)

    metrics = Metrics()

    print(f"\nRunning: {algo_label}")
    print("-" * 50)

    if args.algorithm == "min_conflicts":
        assignment, metrics = algo_fn(csp, max_steps=args.max_steps, metrics=metrics)
    else:
        assignment, metrics = algo_fn(csp, var_h_fn, val_h_fn, metrics=metrics)

    print_solution(assignment, csp, meta, algo_label, metrics, algo_name=args.algorithm)


def main():
    args = parse_args()

    # GUI mode
    if args.gui:
        try:
            import gui
            gui.launch()
        except ImportError as e:
            print(f"GUI error: {e}")
        return

    if args.experiment is not None:
        run_experiment(args.experiment, n_runs=args.runs)
        return

    if args.generate:
        gen = InstanceGenerator(
            n_courses=args.courses,
            n_rooms=args.rooms,
            n_slots=args.slots,
            density=args.density,
            tightness=args.tightness,
            seed=args.seed,
        )
        gen.generate(args.output_dir)
        args.input_dir = args.output_dir
        solve_instance(args)
        return

    if args.input_dir is None:
        print("ERROR: Provide --input-dir to solve an instance, or use --generate / --experiment / --gui.")
        print("\nQuick start examples:")
        print("  python main.py --input-dir data/ --algorithm mac")
        print("  python main.py --generate --courses 20 --rooms 16 --density 0.5 --output-dir instances/test/")
        print("  python main.py --experiment 1")
        print("  python main.py --gui")
        sys.exit(1)

    solve_instance(args)


if __name__ == "__main__":
    main()
