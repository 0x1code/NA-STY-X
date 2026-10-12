"""Compatibility entry point for CURRENT build evidence.

Historical v1 results and scripts are preserved under research/snapshots/boolean-v1.
New measurements must not overwrite those historical artifacts.
"""
import argparse
from record_hardened_build import record

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cargo', default='cargo')
    parser.add_argument('--toolchain', default='stable-x86_64-pc-windows-gnu')
    args = parser.parse_args()
    record(args.cargo, args.toolchain)
