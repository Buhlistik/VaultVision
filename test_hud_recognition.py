import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from game_state import health_present,read_name,HEALTH
from detector import crop

class HudRecognitionTests(unittest.TestCase):
    def frame(self): return Image.new('RGB',(1920,1080),(35,30,25))
    def test_warm_lobby_and_gray_border_are_not_health(self):
        im=self.frame(); draw=ImageDraw.Draw(im)
        draw.rectangle((780,1020,1140,1043),fill=(110,65,55))
        draw.line((780,1030,1140,1030),fill=(160,160,160),width=3)
        self.assertFalse(health_present(im))
    def test_scattered_red_is_not_health(self):
        im=self.frame(); draw=ImageDraw.Draw(im)
        for x in range(780,1140,15):
            draw.rectangle((x,1020,x+4,1043),fill=(180,10,15))
        self.assertFalse(health_present(im))
    def test_horizontal_fill_and_low_health(self):
        for width in (40,180,350):
            im=self.frame()
            ImageDraw.Draw(im).rectangle((783,1025,783+width,1037),fill=(170,15,20))
            self.assertTrue(health_present(im))
    def test_icon_fragments_and_split_long_name(self):
        for text in ('(Gt Quarterstaff BALANCED','Gt; Quarterstaff BALANCED','{C*3 Quarterstaff BALANCED'):
            with patch('game_state.ocr',return_value=text):
                self.assertEqual(read_name(self.frame(),'unused'),'QuarterstaffBALANCED')
    def test_overlong_text_rejected(self):
        with patch('game_state.ocr',return_value='a'*33):
            self.assertEqual(read_name(self.frame(),'unused'),'')
