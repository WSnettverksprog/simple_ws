import unittest
from simple_ws import RequestParser


class RequestParserTestMethods(unittest.TestCase):
    def test_valid_request(self):
        rp = RequestParser()
        input_head = "GET / HTTP/1.1\r\n" \
                     "Host: localhost:8080\r\n" \
                     "Connection: Upgrade\r\n" \
                     "Pragma: no-cache\r\n" \
                     "Cache-Control: no-cache\r\n" \
                     "Upgrade: websocket\r\n"

        rp.parse_request(input_head)
        print(rp.headers)
        self.assertEqual(rp.headers["Host"], "localhost:8080", "Asserting correct host")
        self.assertEqual(rp.headers["Connection"], "Upgrade", "Asserting correct connection")
        self.assertEqual(rp.headers["Pragma"], "no-cache", "Asserting correct pragma")
        self.assertEqual(rp.headers["Cache-Control"], "no-cache", "Asserting correct cache-control")
        self.assertEqual(rp.headers["Upgrade"], "websocket", "Asserting correct upgrade")
