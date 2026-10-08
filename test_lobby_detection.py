import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from game_state import GameGate,lobby_present
from screen_reader import ScreenReader

class LobbyTests(unittest.TestCase):
    def lobby_image(self):
        im=Image.new('RGB',(1920,1080))
        ImageDraw.Draw(im).rectangle((32,12,105,79),fill=(180,140,30))
        return im
    def test_gold_and_menu_labels_required(self):
        with patch('game_state.ocr',return_value='Play Season Religion Skills Stash'):
            self.assertTrue(lobby_present(self.lobby_image(),'unused'))
            self.assertFalse(lobby_present(Image.new('RGB',(1920,1080)),'unused'))
        with patch('game_state.ocr',return_value='Legendary'):
            self.assertFalse(lobby_present(self.lobby_image(),'unused'))
    def test_return_lobby_then_next_match(self):
        gate=GameGate(missing_seconds=120)
        for t in range(3): gate.update('OldPlayer',True,False,t)
        gate.update('OtherPlayer',True,True,3)
        self.assertTrue(gate.spectating)
        gate.update('BackgroundOCR',False,False,4,lobby=True)
        self.assertTrue(gate.spectating)
        gate.update('BackgroundOCR',False,False,5,lobby=True)
        self.assertFalse(gate.spectating)
        self.assertTrue(gate.in_lobby)
        for t in (6,7): self.assertFalse(gate.update('NewPlayer',True,False,t)[0])
        self.assertTrue(gate.update('NewPlayer',True,False,8)[0])
    def test_single_lobby_detection_does_not_release_spectator_lock(self):
        gate=GameGate(); gate.update('Other',True,True,0)
        gate.update('',False,False,1,lobby=True)
        for t in range(2,10): self.assertFalse(gate.update('Other',True,False,t)[0])
        self.assertTrue(gate.spectating)
    def test_lobby_disarms_without_spectator_controls(self):
        gate=GameGate()
        for t in range(3): gate.update('Player',True,False,t)
        self.assertFalse(gate.update('noise',True,False,3,lobby=True)[0])
    def test_normal_gameplay_skips_lobby_ocr(self):
        reader=ScreenReader()
        try:
            with patch('screen_reader.lobby_badge_candidate',return_value=False),patch('screen_reader.lobby_present') as lobby,patch('screen_reader.health_present',return_value=True),patch('screen_reader.ocr',return_value='Change View'):
                reader.read(Image.new('RGB',(1920,1080)),'unused',True)
                lobby.assert_not_called()
                self.assertFalse(reader.lobby)
        finally: reader.close()
