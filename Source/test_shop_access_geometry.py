"""Exact GEOS failure regression; preserves polygons, lines and point obstacles."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import unittest
from shapely import from_wkb
from shapely.geometry import LineString,Point,Polygon
from validate_shop_personality_access import inflated_obstacle_union

HERE=Path(__file__).resolve().parent
FIXTURE='shop_access_union_failure_2_16.json.gz'
FIXTURE_SHA256='a5bcbff4245a2dd0cd7ed9e81df48d5e7b1dfdd33c525f3c4feb712b388e2f77'

class AccessGeometryRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=(HERE/'testdata'/FIXTURE).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=FIXTURE_SHA256:raise ValueError('Exact original GEOS failure fixture changed')
        cls.fixture=json.loads(gzip.decompress(raw));cls.pieces=[from_wkb(bytes.fromhex(w)) for w in cls.fixture['pieces']]
    def test_exact_original_mixed_dimension_failure_input(self):
        self.assertEqual(self.fixture['sourceNativeSha256'],'f52f44353420638bb500afd37f04b9c55d7f30ab4da4c369ad4b4c98080e3c46')
        self.assertEqual(collections.Counter(p.geom_type for p in self.pieces),{'Polygon':19315,'LineString':9024,'MultiLineString':38})
        self.assertEqual(len(self.pieces),28377)
    def test_points_lines_and_near_degenerate_polygons_remain_obstacles(self):
        pieces=[Point(0,0),LineString([(2,0),(2,1)]),Polygon([(4,0),(5,0),(5,1e-14)])]
        result=inflated_obstacle_union(pieces,.25)
        self.assertTrue(result.is_valid)
        for p in pieces:self.assertTrue(result.covers(p))
        for xy in [(0,.249),(2.249,.5),(4.5,.249)]:self.assertTrue(result.covers(Point(xy)))
        for xy in [(0,.251),(2.251,.5),(4.5,.251)]:self.assertFalse(result.covers(Point(xy)))
    def test_full_exact_failure_fixture_buffers_without_losing_any_projection(self):
        # Original union-before-buffer threw TopologyException on this exact
        # ordered WKB fixture. Do not require GEOS to retain that old bug.
        result=inflated_obstacle_union(self.pieces,.25)
        self.assertTrue(result.is_valid);self.assertFalse(result.is_empty)
        self.assertTrue(all(result.covers(piece) for piece in self.pieces))

if __name__=='__main__':unittest.main(verbosity=2)
