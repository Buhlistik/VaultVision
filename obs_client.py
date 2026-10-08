import base64
import hashlib
import json
import uuid


class OBS:
    def __init__(self, password='', port=4455):
        import websocket
        self.socket = websocket.create_connection(
            f'ws://127.0.0.1:{port}', timeout=10,
            http_no_proxy=['127.0.0.1', 'localhost'])
        try:
            hello = self._receive('waiting for OBS greeting')
            if hello.get('op') != 0:
                raise RuntimeError('Expected OBS WebSocket 5 greeting. Check the server port and update OBS if necessary.')
            hello = hello['d']
            data = {'rpcVersion': 1, 'eventSubscriptions': 0}
            if 'authentication' in hello:
                if not password:
                    raise RuntimeError('OBS requires a WebSocket password. Copy it from OBS Tools → WebSocket Server Settings into VaultVision.')
                auth = hello['authentication']
                secret = base64.b64encode(hashlib.sha256(
                    (password + auth['salt']).encode()).digest()).decode()
                data['authentication'] = base64.b64encode(hashlib.sha256(
                    (secret + auth['challenge']).encode()).digest()).decode()
            self.socket.send(json.dumps({'op': 1, 'd': data}))
            if self._receive('authenticating with OBS').get('op') != 2:
                raise RuntimeError('OBS identification failed. Check the WebSocket password and server version.')
        except Exception:
            self.socket.close()
            raise

    def _receive(self, stage):
        # recv() hides the server close frame as an empty string. Preserve
        # the close code so authentication failures have actionable messages.
        import websocket
        try:
            opcode, payload = self.socket.recv_data(control_frame=True)
        except websocket.WebSocketTimeoutException as exc:
            raise RuntimeError(f'OBS timed out while {stage}. Check that OBS is running and its WebSocket server is enabled on port 4455.') from exc
        except websocket.WebSocketConnectionClosedException as exc:
            raise RuntimeError(f'OBS disconnected while {stage}. Check the WebSocket password and that OBS is still running.') from exc
        if opcode == websocket.ABNF.OPCODE_CLOSE:
            code = int.from_bytes(payload[:2], 'big') if len(payload) >= 2 else None
            reason = payload[2:].decode('utf-8', errors='replace') if len(payload) > 2 else ''
            if code == 4009:
                raise RuntimeError('OBS rejected the WebSocket password. Copy the current password from OBS Tools → WebSocket Server Settings and try again.')
            raise RuntimeError(f'OBS closed the connection while {stage} (code {code}): {reason or "no reason supplied"}. Check OBS WebSocket settings.')
        if not payload:
            raise RuntimeError(f'OBS returned an empty response while {stage}. Check its WebSocket server settings.')
        try:
            reply = json.loads(payload)
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError(f'Invalid OBS response while {stage}. Ensure port 4455 belongs to OBS WebSocket 5.') from exc
        if not isinstance(reply, dict) or 'op' not in reply or 'd' not in reply:
            raise RuntimeError(f'Unexpected OBS response while {stage}. OBS WebSocket 5 is required.')
        return reply

    def request(self, kind, **data):
        ident = str(uuid.uuid4())
        self.socket.send(json.dumps({'op': 6, 'd': {
            'requestType': kind, 'requestId': ident, 'requestData': data}}))
        while True:
            reply = self._receive('requesting ' + kind)
            if reply['op'] == 7 and reply['d']['requestId'] == ident:
                body = reply['d']
                if not body['requestStatus']['result']:
                    raise RuntimeError(body['requestStatus'].get('comment', kind + ' failed'))
                return body.get('responseData', {})

    def close(self):
        self.socket.close()
