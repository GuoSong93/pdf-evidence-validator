import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from make_samples import generate,CASES
from validator import validate,approve,extract_source,candidate_rows,write_report

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.temp=TemporaryDirectory();self.root=Path(self.temp.name);generate(self.root)
 def tearDown(self):self.temp.cleanup()
 def test_valid_is_not_automatically_approved(self):
  result=validate(self.root/'normal.pdf');self.assertTrue(result['valid']);self.assertEqual('PENDING_REVIEW',result['reviewStatus'])
 def test_all_negative_samples_are_rejected(self):
  for case in CASES[1:]:
   with self.subTest(case=case):self.assertFalse(validate(self.root/f'{case}.pdf')['valid'])
 def test_hallucinated_page_rejected(self):
  p=self.root/'normal.pdf';rows=candidate_rows(extract_source(p));rows[0]['evidence']['page']=99
  self.assertIn('EVIDENCE_NOT_FOUND',' '.join(validate(p,rows)['errors']))
 def test_plausible_but_altered_value_rejected(self):
  p=self.root/'normal.pdf';rows=candidate_rows(extract_source(p));rows[0]['value']='1200.00';rows[0]['ratio']='120.00'
  self.assertFalse(validate(p,rows)['valid'])
 def test_omitted_source_row_rejected(self):
  p=self.root/'normal.pdf';rows=candidate_rows(extract_source(p));rows.pop()
  self.assertIn('SOURCE_COVERAGE',' '.join(validate(p,rows)['errors']))
 def test_negative_values_rejected(self):
  p=self.root/'normal.pdf';rows=candidate_rows(extract_source(p));rows[0]['value']='-10.00'
  self.assertFalse(validate(p,rows)['valid'])
 def test_invalid_candidate_shape_fails_closed(self):
  p=self.root/'normal.pdf';self.assertFalse(validate(p,[{}])['valid'])
 def test_approval_and_changed_file_guard(self):
  p=self.root/'normal.pdf';result=validate(p);approve(result,p,'Demo reviewer');self.assertEqual('APPROVED',result['reviewStatus'])
  p.write_bytes(p.read_bytes()+b'\nchanged')
  with self.assertRaises(ValueError):approve(result,p,'reviewer')
 def test_failed_result_cannot_be_approved(self):
  p=self.root/'wrong-ratio.pdf'
  with self.assertRaises(ValueError):approve(validate(p),p,'reviewer')
 def test_report_contains_source_and_hash(self):
  r=validate(self.root/'normal.pdf');write_report(r,self.root/'out')
  self.assertIn(r['sha256'],(self.root/'out/review.html').read_text())
  self.assertEqual(r['sha256'],json.loads((self.root/'out/result.json').read_text())['sha256'])
if __name__=='__main__':unittest.main()
