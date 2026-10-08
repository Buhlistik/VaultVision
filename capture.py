"""Desktop-only capture: no game process access, injection, or hooks."""
import base64
import io
from PIL import Image


class Capture:
    def __init__(self,obs,source,method='obs',monitor=1,report=lambda text: None):
        self.obs=obs; self.source=source; self.method=method
        self.monitor=monitor; self.report=report; self.desktop=None
        if method=='screen':
            try:
                from mss import mss
                self.desktop=mss()
                if not 1<=monitor<len(self.desktop.monitors):
                    raise ValueError(f'Capture monitor {monitor} does not exist.')
            except Exception:
                self.close()
                raise
        self.report(f'Capture method: {method}; monitor: {monitor}.')

    def grab(self):
        if self.method=='screen':
            shot=self.desktop.grab(self.desktop.monitors[self.monitor])
            # Decode raw BGRA bytes directly: no PNG/base64/WebSocket roundtrip.
            return Image.frombytes('RGB',shot.size,shot.bgra,'raw','BGRX')
        data=self.obs.request('GetSourceScreenshot',sourceName=self.source,
                              imageFormat='jpg',imageCompressionQuality=90,
                              imageWidth=1920,imageHeight=1080)['imageData']
        image=Image.open(io.BytesIO(base64.b64decode(data.split(',',1)[1])))
        image.load()
        return image

    def close(self):
        if self.desktop is not None:
            self.desktop.close(); self.desktop=None
