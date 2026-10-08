import json
import unittest
from unittest.mock import Mock, patch
import websocket
from obs_client import OBS


class Tests(unittest.TestCase):
    def client(self, opcode, payload):
        obs = OBS.__new__(OBS)
        obs.socket = Mock()
        obs.socket.recv_data.return_value = (opcode, payload)
        return obs

    def test_authentication_close(self):
        obs = self.client(websocket.ABNF.OPCODE_CLOSE, (4009).to_bytes(2, 'big') + b'Authentication failed')
        with self.assertRaisesRegex(RuntimeError, 'rejected the WebSocket password'):
            obs._receive('authenticating')

    def test_empty_reply(self):
        with self.assertRaisesRegex(RuntimeError, 'empty response'):
            self.client(1, '')._receive('greeting')

    def test_invalid_json(self):
        with self.assertRaisesRegex(RuntimeError, 'Invalid OBS response'):
            self.client(1, 'not json')._receive('greeting')

    def test_valid_reply(self):
        obs = self.client(1, json.dumps({'op': 2, 'd': {}}))
        self.assertEqual(obs._receive('authentication')['op'], 2)

    def test_missing_password_closes_socket(self):
        sock = Mock()
        sock.recv_data.return_value = (1, json.dumps({'op': 0, 'd': {
            'authentication': {'salt': 'salt', 'challenge': 'challenge'}}}))
        with patch('websocket.create_connection', return_value=sock):
            with self.assertRaisesRegex(RuntimeError, 'requires a WebSocket password'):
                OBS('')
        sock.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
