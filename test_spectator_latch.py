import unittest
from unittest.mock import patch
from PIL import Image
from game_state import GameGate,spectator_present,death_menu_present,recover_death
from screen_reader import ScreenReader


class SpectatorTests(unittest.TestCase):
    def test_third_person_cam_and_ocr_whitespace(self):
        self.assertTrue(spectator_present('Third Person Cam'))
        self.assertTrue(spectator_present('Change\nView N'))
        self.assertTrue(spectator_present('ReportPlayer R'))
        self.assertFalse(spectator_present('Third floor dungeon'))

    def test_death_menu(self):
        self.assertTrue(death_menu_present('Adventure Over'))
        self.assertTrue(death_menu_present('Continue Spectating'))
        self.assertFalse(death_menu_present('Continue'))

    def test_latched_spectating_survives_missed_controls(self):
        g=GameGate(missing_seconds=30)
        for now in range(3): g.update('NerfRogueStill',True,False,now)
        g.update('SilverSp00nSore',True,True,3)
        for now in range(4,100):
            self.assertFalse(g.update('SilverSp00nSore',True,False,now)[0])
        self.assertTrue(g.spectating)
        g.update('',False,False,100)
        g.update('',False,False,129)
        self.assertTrue(g.spectating)
        g.update('',False,False,130)
        self.assertFalse(g.spectating)

    def test_top_menu_disarms_when_bottom_ocr_misses(self):
        reader=ScreenReader()
        try:
            with patch('screen_reader.ocr',side_effect=['noise','Adventure Over']):
                self.assertTrue(reader.read_spectator(Image.new('RGB',(1920,1080)),'unused'))
        finally: reader.close()

    def test_weaponless_skeleton_recovery_after_death_ui(self):
        with patch('game_state.ocr',return_value='Skeleton Swordman killed NerfRogueSHll'):
            event=recover_death(Image.new('RGB',(1920,1080)),'unused','NerfRogueStill',0)
        self.assertEqual(event['killer'],'Skeleton Swordman')
        self.assertEqual(event['victim'],'NerfRogueStill')
        self.assertEqual(event['weapon'],'')

    def test_does_not_assign_unrelated_death(self):
        with patch('game_state.ocr',return_value='Skeleton Swordman killed SomeoneElse'):
            self.assertIsNone(recover_death(Image.new('RGB',(1920,1080)),'unused','NerfRogueStill',0))


if __name__=='__main__': unittest.main()
