import unittest
from game_state import GameGate,spectator_present
class Tests(unittest.TestCase):
    def arm(self,g):
        for t in (0,1,2): g.update('Player',True,False,t)
    def test_three_confirmations(self):
        g=GameGate(); self.assertFalse(g.update('Player',True,False,0)[0])
        self.assertFalse(g.update('Player',True,False,1)[0])
        self.assertTrue(g.update('Player',True,False,2)[0])
    def test_spectator_overrides_complete_hud(self):
        g=GameGate(); self.arm(g)
        self.assertFalse(g.update('OtherPlayer',True,True,3)[0])
    def test_extended_complete_absence(self):
        g=GameGate(); self.arm(g)
        self.assertTrue(g.update('',False,False,3)[0])
        self.assertTrue(g.update('',False,False,7.9)[0])
        self.assertFalse(g.update('',False,False,8)[0])
    def test_partial_missing_does_not_disarm(self):
        g=GameGate(); self.arm(g)
        self.assertTrue(g.update('',True,False,20)[0])
        self.assertTrue(g.update('Player',False,False,40)[0])
    def test_rearm_after_spectating(self):
        g=GameGate(); self.arm(g); g.update('Other',True,True,3)
        for t in range(4,20):
            self.assertFalse(g.update('Other',True,False,t)[0])
        g.update('',False,False,20)
        g.update('',False,False,25)
        for t in (26,27): self.assertFalse(g.update('NewCharacter',True,False,t)[0])
        self.assertTrue(g.update('NewCharacter',True,False,28)[0])
    def test_cannot_arm_with_partial_hud(self):
        g=GameGate()
        for t in range(10): self.assertFalse(g.update('Player',False,False,t)[0])
    def test_spectator_words(self):
        self.assertTrue(spectator_present('Watch Death Cam D\nChange View N'))
        self.assertFalse(spectator_present('Rondel Dagger'))
if __name__=='__main__': unittest.main()
