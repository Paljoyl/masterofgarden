"""Seed replay snapshots while the local server remains online; no HTTP replay."""
import argparse
from pathlib import Path
from config import load_config
from .db import Database
from local_server.replay import import_captures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    if not args.capture.is_file():
        parser.error('capture file does not exist')
    config = load_config()
    database = Database(config.database)
    try:
        before = database.summary()['snapshots']
        count = import_captures(database, (args.capture.resolve(),), config.api_hosts)
        added = database.summary()['snapshots'] - before
        print(f'Capture imported: {count} responses read, {added} new snapshots. No requests sent.')
    finally:
        database.close()


if __name__ == '__main__':
    main()
