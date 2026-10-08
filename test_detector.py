import unittest
from detector import Detector
class Tests(unittest.TestCase):
    def test_attribution_and_duplicate(self):
        d=Detector('Me'); text='Other killed Someone (Sword)\nMe killed Enemy (Dagger)'
        self.assertEqual(d.process(text,0)[0]['kind'],'kill')
        self.assertEqual(d.process(text,1),[])
        self.assertEqual(d.process(text,2),[])
    def test_death_freezes_identity(self):
        d=Detector('Me')
        self.assertEqual(d.process('Skeleton killed Me',0)[0]['kind'],'death')
        for _ in range(5): d.update_name('SpectatedPlayer')
        self.assertEqual(d.name,'Me')
    def test_confirm_name(self):
        d=Detector()
        for _ in range(2): d.update_name('NewCharacter')
        self.assertEqual(d.name,'')
        d.update_name('NewCharacter'); self.assertEqual(d.name,'NewCharacter')
if __name__=='__main__': unittest.main()
