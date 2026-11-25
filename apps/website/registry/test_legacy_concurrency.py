from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import close_old_connections, connection, connections
from django.test import RequestFactory, TransactionTestCase

from .models import LegacyRun, LegacyRunClaim, Participant
from .views import claim_legacy_run


@skipUnless(connection.vendor == "postgresql", "Requires disposable PostgreSQL database")
class PostgreSQLLegacyClaimTests(TransactionTestCase):
    def test_concurrent_claims_for_different_runs_keep_one_open_claim(self):
        participant = Participant.objects.create_user(email="race@example.test", nickname="Race", password="test-only", status="verified")
        runs = [LegacyRun.objects.create(source_key=f"race-{index}", normalized_legacy_name=f"race-{index}", legacy_participant_name=f"Race {index}") for index in range(2)]
        barrier = Barrier(2)

        def claim(run_id):
            close_old_connections()
            try:
                request = RequestFactory().post("/claim/", {"next": "/account/"})
                request.user = Participant.objects.get(pk=participant.pk)
                request.session = {}
                request._messages = FallbackStorage(request)
                barrier.wait(timeout=10)
                return claim_legacy_run(request, run_id).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(list(executor.map(claim, [run.pk for run in runs])), [302, 302])
        self.assertEqual(LegacyRunClaim.objects.filter(participant=participant, status="pending").count(), 1)
