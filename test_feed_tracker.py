import unittest
from unittest.mock import patch
from PIL import Image
from feed_tracker import RowTracker,RowFeedReader,row_box
from detector import Detector

def entry(number,killer='Other'):
    return f'{killer} killed Victim{number:02d} [Sword]'

class RowTests(unittest.TestCase):
    def test_killer_recovers_without_mutating_victim_or_duplicating(self):
        tracker=RowTracker(); detector=Detector('QuarterstaffBALANCED')
        text=tracker.update({9:'QuarterstaffBAVANCED killed chomperspysombraskye [Quarterstaff]'})
        identity=tracker.rows[9]['id']
        self.assertEqual(detector.process(text,0),[])
        text=tracker.update({9:'QuarterstaffBALANCED killed chomperspysombraskye [Quarterstaff]'})
        self.assertEqual(len(detector.process(text,1)),1)
        text=tracker.update({8:'QuarterstaffBALANCED killed chomperspysombraskyE [Quarterstaff]'})
        self.assertEqual(tracker.rows[8]['id'],identity)
        self.assertIn('chomperspysombraskye',text)
        self.assertEqual(detector.process(text,2),[])
    def test_portal_announcements_preserve_physical_row_alignment(self):
        tracker=RowTracker()
        tracker.update({6:entry(1),7:'A blue portal has appeared',8:entry(2),9:entry(3)})
        identity=tracker.rows[8]['id']
        tracker.update({4:entry(1),5:'A blue portal has appeared',6:entry(2),7:entry(3),8:entry(4),9:entry(5)})
        self.assertEqual(tracker.last_shift,2)
        self.assertEqual(tracker.rows[6]['id'],identity)
    def test_long_entries_keep_left_edge_of_killer(self):
        self.assertLessEqual(row_box(9)[0]*1920,1339)
    def test_partial_feed_appends_without_moving_existing_entries(self):
        tracker=RowTracker()
        tracker.update({0:entry(0),1:entry(1)})
        ids={row:track['id'] for row,track in tracker.rows.items()}
        tracker.update({0:entry(0),1:entry(1),2:entry(2),3:entry(3)})
        self.assertEqual(tracker.last_shift,0)
        self.assertEqual(tracker.rows[0]['id'],ids[0])
        self.assertEqual(tracker.rows[1]['id'],ids[1])
        self.assertEqual(len(tracker.rows),4)
    def test_full_feed_shifts_on_unrelated_kill(self):
        tracker=RowTracker(); tracker.update({row:entry(row) for row in range(10)})
        ids=[tracker.rows[row]['id'] for row in range(10)]
        tracker.update({**{row:entry(row+1) for row in range(9)},9:entry(20,'SomeoneElse')})
        self.assertEqual(tracker.last_shift,1)
        self.assertEqual([tracker.rows[row]['id'] for row in range(9)],ids[1:])
        self.assertNotIn(tracker.rows[9]['id'],ids)
    def test_multiple_new_entries_between_scans(self):
        tracker=RowTracker(); tracker.update({row:entry(row) for row in range(10)})
        ids=[tracker.rows[row]['id'] for row in range(10)]
        tracker.update({**{row:entry(row+3) for row in range(7)},**{row:entry(row+20) for row in range(7,10)}})
        self.assertEqual(tracker.last_shift,3)
        self.assertEqual([tracker.rows[row]['id'] for row in range(7)],ids[3:])
    def test_shift_preserves_clean_player_read_when_one_row_is_unreadable(self):
        tracker=RowTracker(); detector=Detector('QuarterstaffBALANCED')
        original={0:entry(0),1:entry(1),2:'QuarterstaffBALANCED killed LVL3Dispenser [Zweihander]',3:entry(3)}
        self.assertEqual(len(detector.process(tracker.update(original),0)),1)
        text=tracker.update({0:entry(1),1:'QuarterstaffBALANCEDRilled LVL3Dispenser',2:entry(3),3:entry(4)})
        self.assertEqual(tracker.last_shift,1)
        self.assertIn('QuarterstaffBALANCED killed LVL3Dispenser',text)
        self.assertEqual(detector.process(text,1),[])
    def test_compass_prefix_does_not_change_track_identity(self):
        tracker=RowTracker()
        tracker.update({0:'345 N QuarterstaffBALANCED killed headstash [Zweihander]'})
        identity=tracker.rows[0]['id']
        tracker.update({0:'65 N QuarterstaffBALANCED killed headstash [Zweihander]'})
        self.assertEqual(tracker.rows[0]['id'],identity)
    def test_reset_does_not_carry_previous_match_entries(self):
        tracker=RowTracker(); tracker.update({0:entry(1)})
        tracker.reset()
        self.assertEqual(tracker.update({}),'')
    def test_uncertain_shift_does_not_move_unreadable_entries(self):
        tracker=RowTracker(); tracker.update({0:entry(0),1:entry(1),2:entry(2)})
        tracker.update({0:entry(1)})
        self.assertEqual(len(tracker.rows),1)
    def test_pixel_identical_rows_reuse_ocr(self):
        reader=RowFeedReader(); image=Image.new('RGB',(1920,1080))
        try:
            with patch('feed_tracker.ocr',return_value='Other killed Victim [Sword]') as recognize:
                reader.read(image,'unused'); self.assertEqual(recognize.call_count,10)
                reader.read(image,'unused'); self.assertEqual(recognize.call_count,10)
                image.putpixel((1500,145),(255,255,255))
                reader.read(image,'unused'); self.assertEqual(recognize.call_count,11)
        finally: reader.close()

