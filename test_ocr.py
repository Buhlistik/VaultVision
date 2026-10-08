import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from detector import ocr

class Tests(unittest.TestCase):
    def test_file_output_without_console_streams(self):
        def run(args, **kwargs):
            Path(args[2]+'.txt').write_text('Me killed Enemy (Sword)', encoding='utf-8')
            return subprocess.CompletedProcess(args, 0, stdout=None, stderr=None)
        with patch('detector.subprocess.run', side_effect=run):
            self.assertEqual(ocr(Image.new('RGB',(20,20))), 'Me killed Enemy (Sword)')

    def test_failure_without_stderr(self):
        with patch('detector.subprocess.run', return_value=subprocess.CompletedProcess([],1)):
            with self.assertRaisesRegex(RuntimeError, 'Tesseract failed'):
                ocr(Image.new('RGB',(20,20)))

    def test_missing_executable(self):
        with patch('detector.subprocess.run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(RuntimeError, 'Tesseract was not found'):
                ocr(Image.new('RGB',(20,20)))

    def test_no_output_file(self):
        with patch('detector.subprocess.run', return_value=subprocess.CompletedProcess([],0)):
            with self.assertRaisesRegex(RuntimeError, 'did not create OCR output'):
                ocr(Image.new('RGB',(20,20)))

if __name__=='__main__': unittest.main()
