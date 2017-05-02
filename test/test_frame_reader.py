import unittest
from simple_ws import FrameReader


class FrameReaderTestMethods(unittest.TestCase):
    def test_continuation_frame(self):
        fr = FrameReader()

        frame_1 = b'\x01\x83\x00\x00\x00\x00hei'
        frame_2 = b'\x80\x83\x00\x00\x00\x00 du'

        res1 = fr.read_message(frame_1)[1]
        res2 = fr.read_message(frame_2)[1]

        self.assertEqual(res1, None)
        self.assertEqual("hei du", res2.decode('utf-8'))
