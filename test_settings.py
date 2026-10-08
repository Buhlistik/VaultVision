import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from local_settings import load_settings,save_settings
from game_state import GameGate
class Tests(unittest.TestCase):
    def test_round_trip_all_settings(self):
        with tempfile.TemporaryDirectory() as folder, patch('local_settings.password_path',return_value=Path(folder)/'password.txt'):
            expected={'source':'Game','hud_timeout':'90','save_delay':'10','tesseract':'ocr.exe',
                      'character_override':'','volume':.4,'muted':True,'window_geometry':'1480x850+0+0'}
            save_settings(expected); self.assertEqual(load_settings(),expected)
    def test_bad_file_falls_back(self):
        with tempfile.TemporaryDirectory() as folder, patch('local_settings.password_path',return_value=Path(folder)/'password.txt'):
            (Path(folder)/'settings.json').write_text('invalid')
            self.assertEqual(load_settings(),{})
    def test_loading_transition_respects_custom_timeout(self):
        gate=GameGate(missing_seconds=30)
        for t in range(3): gate.update('Player',True,False,t)
        gate.update('',False,False,3)
        self.assertTrue(gate.update('',False,False,20)[0])
        self.assertFalse(gate.update('',False,False,33)[0])
    def test_spectator_disarms_even_with_long_timeout(self):
        gate=GameGate(missing_seconds=600)
        for t in range(3): gate.update('Player',True,False,t)
        self.assertFalse(gate.update('Other',True,True,3)[0])
if __name__=='__main__': unittest.main()
