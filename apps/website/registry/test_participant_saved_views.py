from django.test import TestCase
from django.urls import reverse
from .models import ParticipantSavedView
from .test_submission_policy import SubmissionPolicyTests


class ParticipantSavedViewTests(TestCase):
    setUp = SubmissionPolicyTests.setUp

    def test_tabs_filtering_and_explicit_clear(self):
        self.client.force_login(self.staff)
        url = reverse('admin:registry_participant_changelist')
        view = ParticipantSavedView.objects.get(system_key='all')
        response = self.client.get(url, {'view': view.pk, 'q': 'not-a-participant'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['cl'].result_count, 0)
        self.assertContains(response, 'Saved participant views')
        response = self.client.get(url, {'view': view.pk, '_filters': '1'})
        self.assertGreater(response.context_data['cl'].result_count, 0)
        self.assertEqual(self.client.get(url).context_data['cl'].query, '')

    def test_create_and_private_visibility(self):
        self.client.force_login(self.staff)
        url = reverse('admin:registry_participant_changelist')
        response = self.client.post(url, {'saved_view_action': 'create', 'name': 'My participants', 'q': 'Test'})
        self.assertEqual(response.status_code, 302)
        view = ParticipantSavedView.objects.get(name='My participants')
        self.assertEqual(view.owner, self.staff)
        from .participant_saved_views import available
        self.assertFalse(available(self.owner).filter(pk=view.pk).exists())
        response = self.client.get(url, {'view': view.pk})
        self.assertEqual(response.context_data['cl'].query, 'Test')
