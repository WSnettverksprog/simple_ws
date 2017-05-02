import unittest
from simple_ws import WebSocketFrame


class WebSocketFrameTestMethods(unittest.TestCase):
    def test_construct_parse(self):
        frame = WebSocketFrame(opcode=WebSocketFrame.TEXT, payload="Test", max_frame_size=8192)
        data = frame.construct()

        # Should only be 1 frame with max_frame_size=8192
        if len(data) != 1:
            self.fail("More than 1 frame")

        data = data[0]

        decoded_frame = WebSocketFrame(raw_data=data,ignore_mask=True)

        self.assertEqual(frame.opcode, decoded_frame.opcode)
        self.assertEqual(frame.payload, bytes(decoded_frame.payload))
