"""Audit measured card/light-frame bounds. Does not inspect pixels or approve visuals."""
import argparse
import json
import math
from pathlib import Path
import sys


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


def box(value, label):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f'{label} must be [left, top, right, bottom]')
    result = [finite(v, label) for v in value]
    if result[2] <= result[0] or result[3] <= result[1]:
        raise ValueError(f'{label} must have positive width and height')
    return result


def audit(data):
    if not isinstance(data, dict):
        raise ValueError('Input must be a JSON object')
    if data.get('coordinate_space') != 'output_half_pixels':
        raise ValueError('Convert target and observed bounds to output_half_pixels first')
    tolerance = finite(data['max_edge_error_px'], 'max_edge_error_px')
    if tolerance < 0:
        raise ValueError('max_edge_error_px must be nonnegative')
    samples = data['samples']
    if not isinstance(samples, list) or not samples:
        raise ValueError('At least one measured sample is required')
    results = []
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError('Each sample must be an object')
        clip = sample['clip_id'];frame = sample['frame'];phase = sample['phase']
        if not isinstance(clip, str) or not clip.strip() or not isinstance(phase, str) or not phase.strip():
            raise ValueError('clip_id and phase must be nonempty strings')
        if type(frame) is not int or frame < 0:
            raise ValueError('frame must be a nonnegative integer')
        key = (clip, frame)
        if key in seen:
            raise ValueError(f'Duplicate measured frame: {key}')
        seen.add(key)
        if sample.get('measurement_kind') not in ('manual_frame_measurement', 'pixel_detection'):
            raise ValueError('Use observed frame measurements, not planned/configuration-projected bounds')
        if not isinstance(sample.get('evidence'), str) or not sample['evidence'].strip():
            raise ValueError('Each measurement needs an evidence reference')
        target = box(sample['card_bounds'], 'card_bounds')
        measured = box(sample['light_frame_bounds'], 'light_frame_bounds')
        errors = [m-t for m,t in zip(measured,target)]
        center = [(errors[0]+errors[2])/2, (errors[1]+errors[3])/2]
        ratio_error = ((measured[2]-measured[0])/(measured[3]-measured[1])) / ((target[2]-target[0])/(target[3]-target[1])) - 1
        worst = max(map(abs, errors))
        results.append({'clip_id':clip, 'frame':frame, 'phase':phase,
                        'edge_error_px':dict(zip(('left','top','right','bottom'), errors)),
                        'center_error_px':center, 'ratio_error_fraction':ratio_error,
                        'max_edge_error_px':worst, 'evidence':sample['evidence'],
                        'status':'PASS' if worst <= tolerance else 'FAIL'})
    return {'status':'PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
            'scope':'numeric comparison of supplied frame measurements only',
            'threshold_px':tolerance, 'samples':results,
            'pixel_evidence_verified':False, 'visual_review':'not_performed',
            'normal_speed_review':'not_performed', 'user_acceptance':'not_determined'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    try:
        result = audit(json.loads(args.input.read_text(encoding='utf-8-sig')))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
        print(json.dumps({'status':result['status'], 'samples':len(result['samples']), 'report':str(args.report)}, ensure_ascii=False))
        return 0 if result['status']=='PASS' else 1
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(json.dumps({'status':'ERROR', 'error':str(e)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
