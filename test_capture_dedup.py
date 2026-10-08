import base64
import io
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PIL import Image
from capture import Capture
from detector import Detector


class CaptureDedupTests(unittest.TestCase):
    def test_logged_ocr_variants_save_once(self):
        for first,second in [('SorckinIt','Sor kinIt'),('Huazhouxi','Huazhouxt')]:
            d=Detector('NerfRogueStill')
            self.assertEqual(len(d.process(f'NerfRogueStill killed {first} (Castillon Dagger)',0)),1)
            self.assertEqual(d.process(f'NerfRogueStill killed {second} (Castillon Dagger)',12),[])
            self.assertEqual(d.process(f'NerfRogueStill killed {first} (Castillon Dagger)',24),[])

    def test_two_different_rapid_kills_both_save(self):
        d=Detector('Me')
        self.assertEqual(len(d.process('Me killed SorckinIt [Dagger]',0)),1)
        self.assertEqual(len(d.process('Me killed Huazhouxi [Dagger]',1)),1)

    def test_similar_players_visible_as_separate_rows(self):
        d=Detector('Me')
        d.process('Me killed PlayerOne [Sword]',0)
        self.assertEqual(len(d.process(
            'Me killed PlayerOne [Sword]\nMe killed PlayerOxe [Sword]',1)),1)

    def test_self_death_without_weapon(self):
        d=Detector('NerfRogueStill')
        events=d.process('NerfRogueStill killed NerfRogueStill',0)
        self.assertEqual(events[0]['kind'],'death')
        self.assertEqual(events[0]['weapon'],'')
        self.assertEqual(d.process('Someone killed NerfRogueStill [Sword]',1),[])

    def test_old_event_can_expire(self):
        d=Detector('Me')
        d.process('Me killed EnemyName [Sword]',0)
        d.process('',181)
        self.assertEqual(len(d.process('Me killed EnemyName [Sword]',182)),1)

    def test_obs_jpeg_request_decodes_at_full_resolution(self):
        image=Image.new('RGB',(1920,1080),'red')
        output=io.BytesIO(); image.save(output,format='JPEG',quality=90)
        obs=Mock()
        obs.request.return_value={'imageData':'data:image/jpg;base64,'+
                                  base64.b64encode(output.getvalue()).decode()}
        capture=Capture(obs,'Dark and Darker')
        result=capture.grab()
        self.assertEqual(result.size,(1920,1080))
        self.assertEqual(obs.request.call_args.kwargs['imageFormat'],'jpg')
        self.assertEqual(obs.request.call_args.kwargs['imageCompressionQuality'],90)

    def test_screen_capture_bypasses_obs(self):
        desktop=Mock(); desktop.monitors=[{}, {'left':0,'top':0,'width':2,'height':1}]
        desktop.grab.return_value=SimpleNamespace(size=(2,1),bgra=bytes([0,0,255,0]*2))
        obs=Mock()
        with patch.dict(sys.modules,{'mss':SimpleNamespace(mss=lambda: desktop)}):
            capture=Capture(obs,'unused','screen')
            image=capture.grab()
            self.assertEqual(image.getpixel((0,0)),(255,0,0))
            obs.request.assert_not_called()
            capture.close()
            desktop.close.assert_called_once()


if __name__=='__main__': unittest.main()
