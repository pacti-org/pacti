"""Module that contains the command line application."""

import argparse

from gear.gear import main


def get_parser() -> argparse.ArgumentParser:
    """
    Return the CLI argument parser.

    Returns:
        An argparse parser.
    """
    return argparse.ArgumentParser(prog="gear")


def main_script() -> int:
    parser = get_parser()
    opts = parser.parse_args()
    print(f"script called with arguments: {opts}")
    return 0


def gear() -> int:
    main()
    return 0

