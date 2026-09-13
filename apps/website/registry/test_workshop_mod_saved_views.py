from django.test import TestCase
from django.urls import reverse
from .models import WorkshopModSavedView, WorkshopModWorkspacePreference
from .test_submission_policy import SubmissionPolicyTests


class WorkshopModSavedViewTests(TestCase):
    setUp = SubmissionPolicyTests.setUp

    def test_remembers_tab_and_filters_and_resets(self):
        self.client.force_login(self.staff)
        url = reverse('admin:registry_workshopmod_changelist')
        view = WorkshopModSavedView.objects.get(system_key='allowed')
        response = self.client.get(url, {'view': view.pk, 'q': 'example'})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.context_data['selected_view'], view)
        self.assertEqual(response.context_data['cl'].query, 'example')
        self.assertEqual(WorkshopModWorkspacePreference.objects.get(user=self.staff).last_view, view)
        response = self.client.get(url, {'view': view.pk, 'reset': '1'})
        self.assertEqual(response.context_data['cl'].query, '')
        self.assertContains(response, 'Hidden Tabs')

    def test_personal_view_creation(self):
        self.client.force_login(self.staff)
        url = reverse('admin:registry_workshopmod_changelist')
        response = self.client.post(url, {'saved_view_action': 'create', 'name': 'My mods', 'q': 'example'})
        self.assertEqual(response.status_code, 302)
        view = WorkshopModSavedView.objects.get(name='My mods')
        self.assertEqual(view.owner, self.staff)
        self.assertFalse(view.shared)

    def test_reorder_persists_and_rejects_invalid_order(self):
        self.client.force_login(self.staff)
        url = reverse('admin:registry_workshopmod_changelist')
        self.client.get(url)
        ids = list(WorkshopModSavedView.objects.values_list('pk', flat=True))
        response = self.client.post(url, {'saved_view_action': 'reorder', 'order': list(reversed(ids))})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual([p.view_id for p in response.context_data['saved_tabs']], list(reversed(ids)))
        response = self.client.post(url, {'saved_view_action': 'reorder', 'order': [ids[0], ids[0]]})
        self.assertEqual(response.status_code, 400)
