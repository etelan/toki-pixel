from __future__ import annotations

"""Send one random Toki Pona card to the Pixoo."""

import argparse
import json
import sys
from pathlib import Path


_THIS_DIR = str(Path(__file__).resolve().parent)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from display import PixooHandler, RandomTokiPonaDisplay


DEFAULT_RANDOM_STATE_PATH = Path(__file__).with_name(".random_cycle_state.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection_group = parser.add_mutually_exclusive_group()
    selection_group.add_argument("--toki", help="show one specific toki pona word instead of drawing randomly")
    selection_group.add_argument("--eng", help="show the first toki pona word whose meaning contains this text")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_RANDOM_STATE_PATH,
        help="path used to persist remaining random words between runs",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="discard any saved random cycle before drawing",
    )
    return parser.parse_args()


def load_random_cycle(display: RandomTokiPonaDisplay, state_file: Path) -> None:
    if not state_file.is_file():
        return

    try:
        payload = json.loads(state_file.read_text())
    except (OSError, json.JSONDecodeError):
        return

    names = payload.get("remaining_words")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        return

    try:
        display.data.restore_random_cycle(names)
    except ValueError:
        return


def save_random_cycle(display: RandomTokiPonaDisplay, state_file: Path) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"remaining_words": list(display.data.remaining_random_cycle_names())}
    state_file.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    args = parse_args()
    handler = PixooHandler()
    display = RandomTokiPonaDisplay(handler)

    if args.toki:
        word = display.show(args.toki)
        print(f"sent word: {word.name} - {word.meaning}")
        return

    if args.eng:
        word = display.data.first_matching_meaning(args.eng)
        if word is None:
            raise ValueError(f"unknown english descriptor: {args.eng}")

        display.handler.show_word(word)
        print(f"sent word: {word.name} - {word.meaning}")
        return

    if args.reset and args.state_file.exists():
        args.state_file.unlink()

    load_random_cycle(display, args.state_file)
    word = display.random()
    save_random_cycle(display, args.state_file)
    print(f"sent random word: {word.name} - {word.meaning}")


if __name__ == "__main__":
    main()