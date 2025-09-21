import argparse

__all__ = [
    'add_basic_args',
]


def add_basic_args(parser: argparse.ArgumentParser):
    parser.add_argument('--frame-grabber', dest='fg_idx', type=int, default=0)
    parser.add_argument('--camera', dest='cam_idx', type=int, default=0)
    parser.add_argument('--buffer-size', type=int, default=4)

    return parser
