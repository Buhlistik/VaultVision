import unittest
from unittest.mock import Mock, patch
from obs_shutdown import confirm_exit_dialog, stop_replay_buffer


class ShutdownTests(unittest.TestCase):
    def test_waits_for_async_stop(self):
        connection = Mock()
        connection.request.side_effect = [
            {'outputActive': True}, {}, {'outputActive': True}, {'outputActive': False}]
        with patch('obs_shutdown.time.sleep') as sleep:
            stop_replay_buffer(connection)
        self.assertEqual(connection.request.call_args_list[1].args, ('StopReplayBuffer',))
        sleep.assert_called_once_with(.2)

    def test_stop_timeout(self):
        connection = Mock()
        connection.request.return_value = {'outputActive': True}
        with patch('obs_shutdown.time.monotonic', side_effect=[0, 2]):
            with self.assertRaises(RuntimeError):
                stop_replay_buffer(connection, timeout=1)

    def dialog(self, text, label='&Yes'):
        dialog = Mock()
        message = Mock()
        message.window_text.return_value = text
        button = Mock()
        button.window_text.return_value = label
        button.is_enabled.return_value = True
        dialog.descendants.side_effect = lambda control_type: (
            [message] if control_type == 'Text' else [button])
        desktop = Mock()
        desktop.windows.return_value = [dialog]
        return desktop, button

    def test_confirms_only_known_exit_warning(self):
        desktop, button = self.dialog(
            'OBS is still currently active. All streams/recordings will be shut down.')
        self.assertTrue(confirm_exit_dialog(desktop, 123))
        desktop.windows.assert_called_once_with(process=123, title='Active Outputs')
        button.click.assert_called_once_with()

    def test_does_not_confirm_other_warning(self):
        desktop, button = self.dialog('Delete this scene?')
        self.assertFalse(confirm_exit_dialog(desktop, 123))
        button.click.assert_not_called()


if __name__ == '__main__':
    unittest.main()
