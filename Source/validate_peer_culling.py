"""Read-only validator for actual future exports; never rewrites the baseline.

python Source/validate_peer_culling.py PROJECT_ROOT
Optional --visual/--manifest validate a separately supplied candidate export.
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from peer_culling_contract import validate_peer_culling


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--visual', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    path = args.manifest or args.root / 'Assets/TreeTopYokocho/Data/WorldManifest.json'
    try:
        manifest = json.loads(path.read_text())
        ok, detail = validate_peer_culling(args.root, manifest, args.visual)
    except (OSError, ValueError, TypeError) as error:
        ok, detail = False, {'error': str(error)}
    print(json.dumps(dict(status='PASS' if ok else 'FAIL', detail=detail), indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
