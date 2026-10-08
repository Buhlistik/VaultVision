import unittest
from unittest.mock import Mock,patch
from obs_startup import wait_for_replay


class StartupTests(unittest.TestCase):
    def test_wait_for_active_and_stable_buffer(self):
        obs=Mock(); stop=Mock(); stop.is_set.return_value=False; stop.wait.return_value=False
        obs.request.side_effect=[
            {'outputActive':False}, {},
            {'outputActive':False}, {'outputActive':True}, {'outputActive':True}]
        self.assertTrue(wait_for_replay(obs,stop))
        self.assertEqual(sum(c.args==('StartReplayBuffer',) for c in obs.request.call_args_list),1)
        self.assertEqual(stop.wait.call_args.args,(3,))

    def test_existing_active_buffer_requires_confirmation(self):
        obs=Mock(); obs.request.return_value={'outputActive':True}
        stop=Mock(); stop.is_set.return_value=False; stop.wait.return_value=False
        self.assertTrue(wait_for_replay(obs,stop))
        self.assertEqual(obs.request.call_count,2)

    def test_shutdown_cancels_wait(self):
        obs=Mock(); obs.request.return_value={'outputActive':False}
        stop=Mock(); stop.is_set.return_value=False; stop.wait.return_value=True
        self.assertFalse(wait_for_replay(obs,stop))

    def test_inactive_buffer_never_reports_ready(self):
        obs=Mock(); obs.request.return_value={'outputActive':False}
        stop=Mock(); stop.is_set.return_value=False
        with patch('obs_startup.time.monotonic',side_effect=[0,31]):
            with self.assertRaises(RuntimeError): wait_for_replay(obs,stop)


if __name__=='__main__': unittest.main()
