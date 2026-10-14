"""Capture source compatibility only after explicit independent code review.

Requires exact externally reviewed builder/helper hashes. Does not mutate source,
freeze art, approve a palette, or replace any historical oracle.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Source'))
import rpg_runtime_compatibility as c
p = argparse.ArgumentParser()
p.add_argument('--project', type=Path, required=True)
p.add_argument('--reviewed-builder-sha', required=True)
p.add_argument('--reviewed-loader-sha', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
before = c.baseline_runtime()
deps = dict(before)
deps[c.BUILDER] = a.reviewed_builder_sha
deps[c.ADDED_RUNTIME[0]] = a.reviewed_loader_sha
pin = dict(schema=1, version='2.17.0', beforeBuilderSha256=c.LEGACY_BUILDER_SHA256,
           dependencies=deps,
           scope='Independently source-reviewed runtime light and exact clone routing only. No art or final world approval.')
c.verify_runtime(a.project, oracle=pin)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(pin, indent=2, sort_keys=True) + '\n')
print(json.dumps(dict(output=str(a.output), oracleSha256=c.sha(a.output.read_bytes()),
                     reviewedBuilderSha256=a.reviewed_builder_sha, reviewedLoaderSha256=a.reviewed_loader_sha,
                     note='Independent reviewer must approve this checkpoint before setting ORACLE_SHA256.'), indent=2))
