import asyncio
import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase
import uvicorn

from operations.process_control import stop_requested
from operations.management.commands.run_hosted_web import HostedServer


class ProcessControlTests(SimpleTestCase):
    def test_only_matching_request_stops_web(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / 'request'
            with patch.dict(os.environ, RR_PROCESS_STOP_FILE=str(request), RR_PROCESS_STOP_TOKEN='current'):
                self.assertFalse(stop_requested())
                request.write_text('previous-run')
                self.assertFalse(stop_requested())
                request.write_text('current')
                server = HostedServer(uvicorn.Config('config.asgi:application'))
                self.assertTrue(asyncio.run(server.on_tick(1)))
                self.assertTrue(server.should_exit)

    def test_worker_finishes_current_job_then_stops_before_more_work(self):
        module = 'operations.management.commands.run_reference_update_worker.'
        job = MagicMock()
        job.operation = 'update'
        with patch(module + 'WorkerHeartbeat') as heartbeat, \
             patch(module + 'stop_requested', side_effect=[False, True]), \
             patch(module + 'claim_next_reference_update', return_value=job) as claim, \
             patch(module + 'run_reference_update') as work, \
             patch(module + 'publish_daily_leaderboard') as publish:
            call_command('run_reference_update_worker')
        work.assert_called_once_with(job)
        job.refresh_from_db.assert_called_once()
        claim.assert_called_once()
        publish.assert_not_called()
        heartbeat.return_value.stop.assert_called_once()

    def test_worker_stop_before_claim_does_not_take_a_job(self):
        module = 'operations.management.commands.run_reference_update_worker.'
        with patch(module + 'WorkerHeartbeat') as heartbeat, \
             patch(module + 'stop_requested', return_value=True), \
             patch(module + 'claim_next_reference_update') as claim:
            call_command('run_reference_update_worker')
        claim.assert_not_called()
        heartbeat.return_value.stop.assert_called_once()
