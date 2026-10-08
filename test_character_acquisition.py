import unittest
from unittest.mock import patch
from PIL import Image
from game_state import read_name,GameGate
from detector import NAME,Detector


class CharacterTests(unittest.TestCase):
    def test_long_character_name_is_valid_and_crop_is_wider(self):
        with patch('game_state.ocr',return_value='QuarterstaffBalanced') as recognize:
            self.assertEqual(read_name(Image.new('RGB',(1920,1080)),'unused'),'QuarterstaffBalanced')
        self.assertEqual(recognize.call_args.args[0].width,384)

    def test_name_can_be_confirmed_after_health_arms(self):
        gate=GameGate(); detector=Detector()
        for now in range(3): gate.update('',True,False,now)
        self.assertTrue(gate.armed)
        self.assertEqual(detector.name,'')
        for _ in range(3): detector.update_name('QuarterstaffBalanced')
        self.assertEqual(detector.name,'QuarterstaffBalanced')
        self.assertEqual(detector.process('QuarterstaffBalanced killed Enemy [Quarterstaff]',10)[0]['kind'],'kill')


if __name__=='__main__': unittest.main()
