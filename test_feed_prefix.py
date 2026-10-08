import unittest
from detector import Detector
class FeedPrefixTests(unittest.TestCase):
    def test_compass_prefix_accepts_complete_character_token(self):
        d=Detector('QuarterstaffBALANCED')
        events=d.process('345 JN QuarterstaffBALANCED killed SHmompiss2 (Zweihander)',0)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['killer'],'QuarterstaffBALANCED')
        self.assertEqual(events[0]['kind'],'kill')
    def test_changing_compass_prefix_is_not_another_kill(self):
        d=Detector('QuarterstaffBALANCED')
        self.assertEqual(len(d.process('345 JN QuarterstaffBALANCED killed SHmompiss2 (Zweihander)',0)),1)
        self.assertEqual(d.process('65 (08 QuarterstaffBALANCED killed SHmompiss2 (Zweihander)',10),[])
    def test_embedded_or_longer_other_player_name_is_rejected(self):
        for killer in ('OtherQuarterstaffBALANCED','QuarterstaffBALANCEDExtra','QuarterstaffBALANCED OtherPlayer'):
            self.assertEqual(Detector('QuarterstaffBALANCED').process(killer+' killed Victim (Sword)',0),[])
    def test_self_death_with_prefix_is_still_death(self):
        event=Detector('QuarterstaffBALANCED').process('345 N QuarterstaffBALANCED killed QuarterstaffBALANCED',0)[0]
        self.assertEqual(event['kind'],'death')
