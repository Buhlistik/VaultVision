"""Concurrent screen OCR; gameplay checks still gate every event."""
from concurrent.futures import ThreadPoolExecutor
from detector import crop,ocr,FEED
from feed_tracker import RowFeedReader
from game_state import read_name,health_present,spectator_present,SPECTATOR,death_menu_present,DEATH_MENU,lobby_present,lobby_badge_candidate


class ScreenReader:
    def __init__(self):
        self.lobby=False
        self.feed_reader=RowFeedReader()
        self.pool=ThreadPoolExecutor(max_workers=3,thread_name_prefix='screen-ocr')

    def read_spectator(self,image,executable):
        if spectator_present(ocr(crop(image,SPECTATOR),executable,6)): return True
        return death_menu_present(ocr(crop(image,DEATH_MENU),executable,6))

    def read_feed(self,image,executable):
        return self.feed_reader.read(image,executable,recognize=ocr)

    def read(self,image,executable,armed,need_name=False):
        self.lobby=False
        health=health_present(image)
        # The cheap gold-badge test avoids additional OCR during gameplay.
        lobby_task=self.pool.submit(lobby_present,image,executable) if lobby_badge_candidate(image) else None
        spectator_task=self.pool.submit(self.read_spectator,image,executable)
        # Identity is frozen during a match. Only read it again when needed
        # to arm or to establish that BOTH HUD elements have disappeared.
        name_task=None
        if not armed or not health or need_name:
            name_task=self.pool.submit(read_name,image,executable)
        if not armed: self.feed_reader.reset()
        feed_task=self.pool.submit(self.read_feed,image,executable) if armed else None
        self.lobby=lobby_task.result() if lobby_task else False
        spectator=spectator_task.result()
        name='' if self.lobby or spectator or name_task is None else name_task.result()
        feed=feed_task.result() if feed_task else ''
        return name,health,spectator,feed

    def close(self):
        self.pool.shutdown(wait=True,cancel_futures=True)
        self.feed_reader.close()


def replay_description(obs):
    mode=obs.request('GetProfileParameter',parameterCategory='Output',
                     parameterName='Mode')
    category='AdvOut' if (mode.get('parameterValue') or mode.get('defaultParameterValue'))=='Advanced' else 'SimpleOutput'
    info=obs.request('GetProfileParameter',parameterCategory=category,
                     parameterName='RecRBTime')
    seconds=int(info.get('parameterValue') or info.get('defaultParameterValue'))
    return seconds
