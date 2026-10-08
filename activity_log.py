"""Persistent, bounded diagnostics, independent of the visible interface."""
import logging
from logging.handlers import RotatingFileHandler
from local_settings import password_path

def activity_log_path():
    return password_path().parent/'activity.log'

def create_activity_logger():
    logger=logging.getLogger('vaultvision.activity')
    logger.setLevel(logging.INFO); logger.propagate=False
    if logger.handlers: return logger
    path=activity_log_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    handler=RotatingFileHandler(path,maxBytes=5*1024*1024,backupCount=3,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(handler)
    return logger
