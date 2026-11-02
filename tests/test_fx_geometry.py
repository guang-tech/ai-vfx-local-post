import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('fx_geometry', Path(__file__).resolve().parents[1]/'scripts/fx_geometry.py')
fx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fx)


def sample():
    return {'coordinate_space':'output_half_pixels', 'max_edge_error_px':2,
            'samples':[{'clip_id':'card', 'frame':25, 'phase':'hold',
                        'measurement_kind':'manual_frame_measurement', 'evidence':'annotated-frame.png',
                        'card_bounds':[315,361,753,973], 'light_frame_bounds':[315,361,753,973]}]}


class GeometryTests(unittest.TestCase):
    def test_centered_but_wrong_aspect_fails(self):
        data=sample();data['samples'][0]['light_frame_bounds']=[287,374,781,960]
        result=fx.audit(data)
        self.assertEqual(result['samples'][0]['center_error_px'],[0,0])
        self.assertEqual(result['status'],'FAIL')

    def test_project_tolerance_and_review_boundary(self):
        data=sample();data['samples'][0]['light_frame_bounds']=[316,360,755,973]
        result=fx.audit(data)
        self.assertEqual(result['status'],'PASS')
        self.assertFalse(result['pixel_evidence_verified'])
        self.assertEqual(result['normal_speed_review'],'not_performed')
        data['max_edge_error_px']=1
        self.assertEqual(fx.audit(data)['status'],'FAIL')

    def test_later_drift_is_not_hidden_by_first_frame(self):
        data=sample();later=copy.deepcopy(data['samples'][0]);later.update(frame=55,phase='empty_frame',light_frame_bounds=[320,361,758,973])
        data['samples'].append(later)
        self.assertEqual(fx.audit(data)['status'],'FAIL')

    def test_rejects_projected_or_missing_evidence(self):
        for field,value in [('measurement_kind','configuration_projection'),('evidence','')]:
            with self.subTest(field=field):
                data=sample();data['samples'][0][field]=value
                with self.assertRaises(ValueError):fx.audit(data)

    def test_invalid_and_duplicate_data(self):
        for bounds in ([0,0,0,10],[315,361,float('nan'),973],[0,0,True,10]):
            data=sample();data['samples'][0]['light_frame_bounds']=bounds
            with self.assertRaises(ValueError):fx.audit(data)
        data=sample();data['samples']*=2
        with self.assertRaises(ValueError):fx.audit(data)
        data=sample();data['coordinate_space']='native_source_pixels'
        with self.assertRaises(ValueError):fx.audit(data)


if __name__=='__main__':unittest.main()
