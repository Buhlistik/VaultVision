import base64,hashlib,json,uuid
class OBS:
    def __init__(self,password='',port=4455):
        import websocket
        self.socket=websocket.create_connection(f'ws://127.0.0.1:{port}',timeout=10)
        hello=json.loads(self.socket.recv())['d']; data={'rpcVersion':1,'eventSubscriptions':0}
        if 'authentication' in hello:
            a=hello['authentication']
            secret=base64.b64encode(hashlib.sha256((password+a['salt']).encode()).digest()).decode()
            data['authentication']=base64.b64encode(hashlib.sha256((secret+a['challenge']).encode()).digest()).decode()
        self.socket.send(json.dumps({'op':1,'d':data}))
        if json.loads(self.socket.recv())['op']!=2: raise RuntimeError('OBS identification failed')
    def request(self,kind,**data):
        ident=str(uuid.uuid4()); self.socket.send(json.dumps({'op':6,'d':{'requestType':kind,'requestId':ident,'requestData':data}}))
        while True:
            reply=json.loads(self.socket.recv())
            if reply['op']==7 and reply['d']['requestId']==ident:
                body=reply['d']
                if not body['requestStatus']['result']: raise RuntimeError(body['requestStatus'].get('comment',kind+' failed'))
                return body.get('responseData',{})
    def close(self): self.socket.close()
