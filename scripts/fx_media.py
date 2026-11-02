"""Local-only VFX media checks. Python standard library + an explicit FFmpeg."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace')
    if r.returncode:
        raise RuntimeError(r.stderr[-5000:])
    return r


def reserve(path):
    p = Path(path)
    if p.exists():
        raise ValueError(f'Refusing to overwrite: {p}')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def decode(ff, source, hardware=None):
    cmd = [ff, '-hide_banner', '-loglevel', 'debug' if hardware else 'error', '-xerror']
    if hardware:
        cmd += ['-hwaccel', hardware]
    r = run(cmd + ['-i', str(source), '-an', '-pix_fmt', 'yuv420p',
                   '-fps_mode', 'passthrough', '-f', 'framemd5', '-'])
    tb = re.search(r'#tb 0:\s*(\d+/\d+)', r.stdout)
    dims = re.search(r'#dimensions 0:\s*(\d+)x(\d+)', r.stdout)
    rows = [s.split(',') for s in r.stdout.splitlines() if s and not s.startswith('#')]
    if not tb or not dims or not rows:
        raise ValueError('Missing decoded frame metadata')
    # A requested hardware flag is not proof that the decoder used that path.
    markers = ('format d3d11', 'format dxva2', 'format cuda', 'format vaapi',
               'format videotoolbox', 'format qsv')
    hw_evidence = [s for s in r.stderr.splitlines() if any(m in s.lower() for m in markers)]
    return {
        'dimensions': [int(dims[1]), int(dims[2])],
        'time_base': tb[1],
        'pts': [int(row[2]) for row in rows],
        'hashes': [row[-1].strip() for row in rows],
        'hardware_evidence': hw_evidence,
    }


def audit(a):
    report_path = reserve(a.report)
    s = decode(a.ffmpeg, a.input)
    tb = Fraction(s['time_base'])
    pts = [p * tb for p in s['pts']]
    step = 1 / Fraction(str(a.fps))
    checks = {
        'dimensions': s['dimensions'] == [a.width, a.height],
        'frame_count': len(pts) == a.frames,
        'starts_at_zero': pts[0] == 0,
        'continuous_pts': all(abs((y-x)-step) <= min(tb, step/10) for x, y in zip(pts, pts[1:]))
                          and all(y > x for x, y in zip(pts, pts[1:])),
        'max_bytes': Path(a.input).stat().st_size <= a.max_bytes,
    }
    report = {
        'input': str(Path(a.input).resolve()), 'checks': checks,
        'decoded_frames': len(pts), 'dimensions': s['dimensions'],
        'duration_from_pts': float(pts[-1]-pts[0]+step),
        'bytes': Path(a.input).stat().st_size,
        'sha256': hashlib.sha256(Path(a.input).read_bytes()).hexdigest(),
        'visual_review': 'not_performed_by_script', 'client_acceptance': 'not_tested',
    }
    if a.hardware:
        try:
            hw = decode(a.ffmpeg, a.input, a.hardware)
            confirmed = bool(hw['hardware_evidence'])
            same = hw['hashes'] == s['hashes'] and hw['pts'] == s['pts']
            report['hardware'] = {'requested': a.hardware, 'confirmed_by_log': confirmed,
                                  'pixel_and_pts_match': same, 'evidence': hw['hardware_evidence']}
            checks['requested_hardware_verified'] = confirmed and same
        except (RuntimeError, ValueError) as e:
            report['hardware'] = {'requested': a.hardware, 'error': str(e)}
            checks['requested_hardware_verified'] = False
    report['status'] = 'PASS' if all(checks.values()) else 'FAIL'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(report['status'], str(report_path))
    return 0 if report['status'] == 'PASS' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('audit', 'compatible', 'contact'):
        p = sub.add_parser(name)
        p.add_argument('input', type=Path)
        p.add_argument('--ffmpeg', default='ffmpeg')
        if name == 'audit':
            for field in ('width', 'height', 'frames', 'max-bytes'):
                p.add_argument('--'+field, type=int, required=True)
            p.add_argument('--fps', required=True, help='Integer, decimal or rational, e.g. 30000/1001')
            p.add_argument('--report', required=True)
            p.add_argument('--hardware', help='Optional decoder, e.g. d3d11va; requires log evidence')
        else:
            p.add_argument('--output', required=True)
            if name == 'compatible':
                p.add_argument('--fps', required=True)
                p.add_argument('--maxrate', required=True)
                p.add_argument('--crf', type=int, default=18)
            else:
                p.add_argument('--frames', type=int, required=True, help='Decoded frame count for whole-clip sheet')
                p.add_argument('--columns', type=int, default=10)
    a = parser.parse_args()
    if not a.input.is_file():
        raise ValueError(f'Input not found: {a.input}')
    if a.command == 'audit':
        if min(a.width, a.height, a.frames, a.max_bytes) <= 0 or Fraction(a.fps) <= 0:
            raise ValueError('Expected dimensions, frames, fps and size must be positive')
        return audit(a)
    out = reserve(a.output)
    cmd = [a.ffmpeg, '-n', '-hide_banner', '-v', 'error', '-xerror', '-i', str(a.input)]
    if a.command == 'compatible':
        if Fraction(a.fps) <= 0:
            raise ValueError('fps must be positive')
        cmd += ['-an', '-c:v', 'libx264', '-profile:v', 'baseline', '-crf', str(a.crf),
                '-g', '1', '-bf', '0', '-refs', '1', '-maxrate', a.maxrate,
                '-bufsize', a.maxrate, '-pix_fmt', 'yuv420p', '-r', a.fps,
                '-fps_mode', 'cfr', '-movflags', '+faststart', str(out)]
    else:
        if min(a.frames, a.columns) <= 0:
            raise ValueError('frames and columns must be positive')
        rows = math.ceil(a.frames/a.columns)
        cmd += ['-vf', f'scale=320:-2,tile={a.columns}x{rows}', '-frames:v', '1', '-update', '1', str(out)]
    run(cmd)
    print(str(out))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
