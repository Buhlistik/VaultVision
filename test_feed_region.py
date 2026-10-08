import unittest
from PIL import Image
from detector import FEED, crop, Detector

class Tests(unittest.TestCase):
    def test_tenth_row_is_in_capture(self):
        image = Image.new('RGB', (1920,1080))
        image.putpixel((1500,210), (255,0,0))
        region=crop(image,FEED)
        self.assertEqual(region.getpixel((1500-round(FEED[0]*1920),210)), (255,0,0))
        self.assertGreaterEqual(region.height,230)

    def test_ninth_row_triggers_without_moving_up(self):
        text='\n'.join([f'Other{i} killed Victim{i} (Sword)' for i in range(8)]+
                       ['NerfRogueStill killed GreatVigil (Castillon Dagger)',
                        'Other9 killed Victim9 (Sword)'])
        d=Detector('NerfRogueStill')
        events=d.process(text,0)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['kind'],'kill')
        self.assertEqual(d.process(text,.5),[])
        self.assertEqual(d.process(text,1),[])

if __name__=='__main__': unittest.main()
