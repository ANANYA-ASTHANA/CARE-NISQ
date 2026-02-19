import argparse
from src.runners import calibrate, main_grid, robustness
from src.analysis import summarize, plotting


def main():
    parser = argparse.ArgumentParser(
        description="CARE-NISQ: Constraint-Aware Regime Evaluation for NISQ Systems"
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("calibrate", help="Calibrate cutting sampling budget")
    subparsers.add_parser("run-main", help="Run full experimental grid")
    subparsers.add_parser("run-robustness", help="Run robustness subsets")
    subparsers.add_parser("summarize", help="Aggregate results")
    subparsers.add_parser("plot", help="Generate plots")

    args = parser.parse_args()

    if args.command == "calibrate":
        calibrate.run()
    elif args.command == "run-main":
        main_grid.run()
    elif args.command == "run-robustness":
        robustness.run()
    elif args.command == "summarize":
        summarize.run()
    elif args.command == "plot":
        plotting.run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
