"""Freeze/verify explicitly selected project files. No rendering or deletion."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inside(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError(f'Not a project-relative path: {relative}')
    p = root / rel
    for item in [p, *p.parents]:
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise ValueError(f'Linked paths are unsupported: {relative}')
    if not p.resolve().is_relative_to(root):
        raise ValueError(f'Path escapes project: {relative}')
    return p


def snapshot(root, paths, output):
    if output.exists():
        raise ValueError('Manifest exists; use a new filename')
    records = {}
    for rel in paths:
        p = inside(root, rel)
        if not p.exists():
            raise ValueError(f'Missing dependency: {rel}')
        targets = p.rglob('*') if p.is_dir() else [p]
        for candidate in targets:
            candidate = inside(root, candidate.relative_to(root))
            if candidate.is_file():
                key = candidate.relative_to(root).as_posix()
                if candidate.resolve() == output.resolve():
                    raise ValueError('Manifest cannot include itself')
                records[key] = {'path': key, 'bytes': candidate.stat().st_size, 'sha256': digest(candidate)}
    if not records:
        raise ValueError('No files selected')
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {'schema_version': 1, 'files': [records[k] for k in sorted(records)]}
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    return {'status': 'PASS', 'files': len(records), 'bytes': sum(x['bytes'] for x in records.values())}


def verify(root, data):
    issues = []
    seen = set()
    for item in data['files']:
        rel = item['path']
        if rel in seen:
            raise ValueError(f'Duplicate manifest path: {rel}')
        seen.add(rel)
        p = inside(root, rel)
        if not p.is_file():
            issues.append({'path': rel, 'reason': 'missing'})
        elif p.stat().st_size != item['bytes'] or digest(p) != item['sha256']:
            issues.append({'path': rel, 'reason': 'changed'})
    if not seen:
        raise ValueError('Empty manifest')
    return {'status': 'FAIL' if issues else 'PASS', 'files': len(seen), 'issues': issues}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ['snapshot', 'verify']:
        s = sub.add_parser(name)
        s.add_argument('--root', type=Path, required=True)
        if name == 'snapshot':
            s.add_argument('--paths', type=Path, required=True, help='JSON array of relative files/directories')
            s.add_argument('--output', type=Path, required=True)
        else:
            s.add_argument('--manifest', type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve(strict=True)
    try:
        if args.command == 'snapshot':
            result = snapshot(root, json.loads(args.paths.read_text(encoding='utf-8-sig')), args.output)
        else:
            result = verify(root, json.loads(args.manifest.read_text(encoding='utf-8-sig')))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'PASS' else 1
    except (OSError, ValueError, KeyError) as e:
        print(json.dumps({'status': 'ERROR', 'error': str(e)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
