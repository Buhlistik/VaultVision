import threading
import unittest
from unittest.mock import Mock,patch
from PIL import Image
from detector import Detector
from screen_reader import ScreenReader,replay_description


class TimingTests(unittest.TestCase):
    def test_newest_of_ten_rows_triggers_on_first_scan(self):
        lines=[f'Other{i} killed Enemy{i} [Sword]' for i in range(9)]
        lines.append('ScreamLikeAGirl killed Moneyman5 [Quarterstaff]')
        detector=Detector('ScreamLikeAGirl')
        events=detector.process('\n'.join(lines),0)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['weapon'],'Quarterstaff')
        self.assertEqual(detector.process('\n'.join(lines),.5),[])

    def test_bracketed_death(self):
        event=Detector('Me').process('Enemy killed Me [Sword]',0)[0]
        self.assertEqual(event['kind'],'death')

    def test_feed_and_spectator_ocr_overlap_and_skip_redundant_name(self):
        barrier=threading.Barrier(2)
        def recognize(*args):
            barrier.wait(timeout=2)
            return 'change view'
        reader=ScreenReader()
        try:
            with patch('screen_reader.health_present',return_value=True), \
                 patch('screen_reader.read_name') as name, \
                 patch('screen_reader.ocr',side_effect=recognize):
                result=reader.read(Image.new('RGB',(1920,1080)),'unused',True)
                self.assertTrue(result[2])
                self.assertEqual(result[0],'')
                name.assert_not_called()
        finally:
            reader.close()

    def test_read_name_if_health_disappears(self):
        reader=ScreenReader()
        try:
            with patch('screen_reader.health_present',return_value=False), \
                 patch('screen_reader.read_name',return_value='Me') as name, \
                 patch('screen_reader.ocr',return_value=''):
                result=reader.read(Image.new('RGB',(1920,1080)),'unused',True)
                self.assertEqual(result[0],'Me')
                name.assert_called_once()
        finally:
            reader.close()

    def test_actual_advanced_replay_duration(self):
        obs=Mock()
        obs.request.side_effect=[
            {'parameterValue':'Advanced'},
            {'parameterValue':'20','defaultParameterValue':'60'}]
        self.assertEqual(replay_description(obs),20)
        self.assertEqual(obs.request.call_args.kwargs['parameterCategory'],'AdvOut')


if __name__=='__main__': unittest.main()
