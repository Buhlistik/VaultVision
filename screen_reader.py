"""Concurrent screen OCR; gameplay checks still gate every event."""
from concurrent.futures import ThreadPoolExecutor
from detector import crop,ocr,FEED
from game_state import read_name,health_present,spectator_present,SPECTATOR


class ScreenReader:
    def __init__(self):
        self.pool=ThreadPoolExecutor(max_workers=3,thread_name_prefix='screen-ocr')

    def read(self,image,executable,armed):
        health=health_present(image)
        spectator_task=self.pool.submit(ocr,crop(image,SPECTATOR),executable,6)
        # Identity is frozen during a match. Only read it again when needed
        # to arm or to establish that BOTH HUD elements have disappeared.
        name_task=None
        if not armed or not health:
            name_task=self.pool.submit(read_name,image,executable)
        feed_task=self.pool.submit(ocr,crop(image,FEED),executable,6) if armed else None
        spectator=spectator_present(spectator_task.result())
        name='' if spectator or name_task is None else name_task.result()
        feed=feed_task.result() if feed_task else ''
        return name,health,spectator,feed

    def close(self):
        self.pool.shutdown(wait=True,cancel_futures=True)


def replay_description(obs):
    mode=obs.request('GetProfileParameter',parameterCategory='Output',
                     parameterName='Mode')
    category='AdvOut' if (mode.get('parameterValue') or mode.get('defaultParameterValue'))=='Advanced' else 'SimpleOutput'
    info=obs.request('GetProfileParameter',parameterCategory=category,
                     parameterName='RecRBTime')
    seconds=int(info.get('parameterValue') or info.get('defaultParameterValue'))
    return seconds
