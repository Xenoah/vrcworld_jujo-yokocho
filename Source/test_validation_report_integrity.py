"""Current input/report binding and count mutations, without rerunning geometry."""
import copy,json,unittest
from pathlib import Path
from validation_report_integrity import checked_shop_access_counts
ROOT=Path(__file__).resolve().parent.parent
class ReportIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=json.loads((ROOT/'Docs/staff_access_validation.json').read_text())
    def test_current(self):self.assertEqual(checked_shop_access_counts(ROOT,self.report),dict(requiredProbes=208,connectedExits=49,largerGuestContacts=13,largerGuestDiagnostics=70))
    def test_mutations(self):
        mutations=[lambda x:x['inputSha256'].update({'VisualMeshes.bytes':'0'*64}),lambda x:x.update(status='FAIL'),lambda x:x['probes'].pop(),lambda x:x['probes'][0].update(passed=False),lambda x:x['connection'][0].update(disconnectedSeats=['S01_Seat_1']),lambda x:x['connection'][0]['seatExitComponents'].update({'S01_Seat_1':[]}),lambda x:x['diagnostics'].pop(),lambda x:x['connection'][0]['seatExitComponents'].update({'S01_Fabricated':x['connection'][0]['seatExitComponents'].pop('S01_Seat_1')})]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                report=copy.deepcopy(self.report);mutate(report)
                with self.assertRaises(ValueError):checked_shop_access_counts(ROOT,report)
if __name__=='__main__':unittest.main()
