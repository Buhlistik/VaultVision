"""Wait for asynchronous OBS replay startup before enabling detection."""
import time


def wait_for_replay(obs,shutdown,timeout=30):
    deadline=time.monotonic()+timeout
    started=False; confirmations=0; start_error=None
    while not shutdown.is_set():
        active=obs.request('GetReplayBufferStatus')['outputActive']
        if active:
            confirmations+=1
            if confirmations>=2:
                # Give the newly confirmed buffer time to accumulate footage.
                return not shutdown.wait(3)
        else:
            confirmations=0
            if not started:
                started=True
                try: obs.request('StartReplayBuffer')
                except RuntimeError as exc:
                    # --startreplaybuffer may already be starting it.
                    start_error=exc
        if time.monotonic()>=deadline:
            raise RuntimeError('OBS replay buffer did not become active within 30 seconds.'
                               + (' '+str(start_error) if start_error else ''))
        if shutdown.wait(1): return False
    return False
