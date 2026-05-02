import json
import os
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import InvitedGuest, RSVPSubmission


class PublicPagesTests(TestCase):
    def test_home(self):
        self.assertEqual(self.client.get(reverse('wedding:home')).status_code, 200)

    def test_our_story(self):
        self.assertEqual(self.client.get(reverse('wedding:our_story')).status_code, 200)

    def test_events(self):
        self.assertEqual(self.client.get(reverse('wedding:events')).status_code, 200)

    def test_rsvp(self):
        self.assertEqual(self.client.get(reverse('wedding:rsvp')).status_code, 200)

    def test_accommodations(self):
        self.assertEqual(self.client.get(reverse('wedding:accommodations')).status_code, 200)

    def test_faq(self):
        self.assertEqual(self.client.get(reverse('wedding:faq')).status_code, 200)

    def test_rsvp_has_plugin_markup(self):
        response = self.client.get(reverse('wedding:rsvp'))
        self.assertContains(response, 'id="aw-rsvp-gate"')
        self.assertContains(response, 'id="aw-rsvp-app"')

    def test_rsvp_has_plugin_config(self):
        response = self.client.get(reverse('wedding:rsvp'))
        self.assertContains(response, 'window.AW_RSVP_CONF')

    def test_rsvp_has_thank_you_card(self):
        response = self.client.get(reverse('wedding:rsvp'))
        self.assertContains(response, 'id="aw-thank-you"')

    def test_rsvp_has_already_rsvped_card(self):
        response = self.client.get(reverse('wedding:rsvp'))
        self.assertContains(response, 'id="aw-already-rsvped"')
        self.assertContains(response, 'id="aw-already-name"')

    # -- WordPress mirror: navbar/hero/static-path expectations -----

    def test_no_navbar_in_base(self):
        # The shared header/nav was removed; pages must not render <nav class="site-nav">
        for url_name in ('home', 'our_story', 'events', 'rsvp', 'accommodations', 'faq'):
            response = self.client.get(reverse('wedding:' + url_name))
            self.assertNotContains(response, 'class="site-nav"', msg_prefix=url_name)
            self.assertNotContains(response, 'class="hamburger"', msg_prefix=url_name)
            self.assertNotContains(response, '<header class="site-header"', msg_prefix=url_name)

    def test_home_has_envelope_section(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'id="envelope-section"')

    def test_home_has_home_content(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'id="home-content"')

    def test_home_has_envelope_img(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'id="envelope-img"')

    def test_home_has_envelope_close_btn(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'id="envelope-close-btn"')

    def test_home_has_closed_envelope_image(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'closed-no-bg.png')

    def test_home_has_open_envelope_image(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'open-no-bg.png')

    def test_our_story_no_hero_section_id(self):
        response = self.client.get(reverse('wedding:our_story'))
        self.assertNotContains(response, 'id="hero-section"')

    def test_events_no_hero_section_id(self):
        response = self.client.get(reverse('wedding:events'))
        self.assertNotContains(response, 'id="hero-section"')

    def test_base_links_favicon(self):
        response = self.client.get(reverse('wedding:home'))
        self.assertContains(response, 'rel="icon"')
        self.assertContains(response, 'bouquet-img.png')

    def test_inner_pages_no_hero_section(self):
        for url_name in ('our_story', 'events', 'rsvp', 'accommodations', 'faq'):
            response = self.client.get(reverse('wedding:' + url_name))
            self.assertNotContains(response, 'id="hero-section"', msg_prefix=url_name)
            self.assertNotContains(response, 'aw-page-hero', msg_prefix=url_name)
            self.assertNotContains(response, 'aw-hero-fullscreen', msg_prefix=url_name)

    def test_pages_use_static_image_paths(self):
        # Page templates must reference /static/wedding/images/, not /media/
        for url_name in ('home', 'our_story', 'events', 'accommodations', 'faq'):
            response = self.client.get(reverse('wedding:' + url_name))
            self.assertContains(response, '/static/wedding/images/', msg_prefix=url_name)
            content = response.content.decode('utf-8')
            self.assertNotIn(
                'src="/media/', content,
                msg='%s still references /media/ for img src' % url_name,
            )

    def test_inner_pages_have_back_arrow(self):
        for url_name in ('our_story', 'events', 'accommodations', 'faq'):
            response = self.client.get(reverse('wedding:' + url_name))
            self.assertContains(response, 'class="back-arrow"', msg_prefix=url_name)

    def test_all_pages_status_200(self):
        for url_name in ('home', 'our_story', 'events', 'rsvp', 'accommodations', 'faq'):
            response = self.client.get(reverse('wedding:' + url_name))
            self.assertEqual(response.status_code, 200, url_name)


class RSVPLookupTests(TestCase):
    def setUp(self):
        self.guest = InvitedGuest.objects.create(
            first_name='Alice', last_name='Smith',
            email='alice@example.com', max_guests=2,
        )

    def _get(self, params):
        return self.client.get(reverse('wedding:rsvp_lookup'), params)

    def test_lookup_by_email(self):
        response = self._get({'email': 'ALICE@example.com'})
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body['found'])
        self.assertFalse(body['multiple'])
        self.assertEqual(body['invite_id'], self.guest.id)
        self.assertEqual(body['full_name'], 'Alice Smith')
        self.assertEqual(body['max_guests'], 2)
        self.assertEqual(body['current_guests'], 0)
        self.assertEqual(body['rsvped'], 0)
        self.assertIsNone(body['rsvp'])

    def test_lookup_by_name_partial(self):
        body = self._get({'first_name': 'Alic'}).json()
        self.assertTrue(body['found'])
        self.assertFalse(body['multiple'])
        self.assertEqual(body['full_name'], 'Alice Smith')

    def test_lookup_by_full_name(self):
        body = self._get({'first_name': 'alice', 'last_name': 'smith'}).json()
        self.assertTrue(body['found'])

    def test_lookup_not_found(self):
        body = self._get({'email': 'nobody@example.com'}).json()
        self.assertEqual(body, {'found': False})

    def test_lookup_no_input(self):
        body = self._get({}).json()
        self.assertEqual(body, {'found': False})

    def test_lookup_multiple_matches(self):
        InvitedGuest.objects.create(first_name='Alice', last_name='Jones')
        body = self._get({'first_name': 'Alice'}).json()
        self.assertTrue(body['found'])
        self.assertTrue(body['multiple'])
        self.assertEqual(len(body['candidates']), 2)
        self.assertIn('id', body['candidates'][0])
        self.assertIn('full_name', body['candidates'][0])

    def test_lookup_returns_existing_rsvp(self):
        sub = RSVPSubmission.objects.create(
            invited_guest=self.guest, attending=True,
            email='alice@example.com', phone='555-1234',
        )
        body = self._get({'email': 'alice@example.com'}).json()
        self.assertIsNotNone(body['rsvp'])
        self.assertEqual(body['rsvp']['email'], 'alice@example.com')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RSVPSubmitTests(TestCase):
    def setUp(self):
        self.guest = InvitedGuest.objects.create(
            first_name='Alice', last_name='Smith',
            email='alice@example.com', max_guests=2,
        )

    def _payload(self, **overrides):
        base = {
            'household': 'Smith Household',
            'invite_id': self.guest.id,
            'maxGuests': 2,
            'events': [{'id': 'ceremony', 'label': 'Ceremony'}, {'id': 'reception', 'label': 'Reception'}],
            'topEventSelections': ['Ceremony', 'Reception'],
            'guests': [
                {'id': 'g1', 'name': 'Alice Smith', 'type': 'adult', 'events': ['Ceremony', 'Reception']},
                {'id': 'g2', 'name': 'Bob Smith',   'type': 'adult', 'events': ['Ceremony']},
            ],
            'contact': {'email': 'alice@example.com', 'phone': '555-1234'},
            'notes': "Can't wait!",
            'notify': 'couple@example.com',
            'secret': settings.RSVP_SECRET,
            'hp': '',
            'submittedAt': '2026-08-01T12:00:00Z',
        }
        base.update(overrides)
        return base

    def _post(self, payload):
        return self.client.post(
            reverse('wedding:rsvp_submit'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_submit_success(self):
        response = self._post(self._payload())
        body = response.json()
        self.assertEqual(response.status_code, 200, body)
        self.assertTrue(body['ok'])

        submission = RSVPSubmission.objects.get(pk=body['id'])
        self.assertEqual(submission.guests.count(), 2)
        self.assertEqual(submission.event_selections.count(), 2)

        guest = InvitedGuest.objects.get(pk=self.guest.id)
        self.assertTrue(guest.rsvped)
        self.assertEqual(guest.current_guests, 2)
        self.assertEqual(len(mail.outbox), 2)

    def test_submit_honeypot_rejects(self):
        response = self._post(self._payload(hp='spam'))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    def test_submit_wrong_secret_rejects(self):
        response = self._post(self._payload(secret='wrong'))
        self.assertEqual(response.status_code, 403)

    def test_submit_empty_guests_rejects(self):
        response = self._post(self._payload(guests=[]))
        self.assertEqual(response.status_code, 422)

    def test_submit_missing_contact_email_rejects(self):
        response = self._post(self._payload(contact={'phone': '555-1234'}))
        self.assertEqual(response.status_code, 422)

    def test_submit_unknown_invite_returns_404(self):
        response = self._post(self._payload(
            invite_id=9999,
            contact={'email': 'unknown@example.com'},
        ))
        self.assertEqual(response.status_code, 404)

    def test_submit_falls_back_to_email_lookup(self):
        # invite_id missing but contact email matches an InvitedGuest
        payload = self._payload()
        payload.pop('invite_id', None)
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    NOTIFICATION_EMAIL='couple@example.com',
    DEFAULT_FROM_EMAIL='zacherylong@aspiredwebsites.com',
)
class RSVPEmailTests(TestCase):
    """Email behaviour around rsvp_submit: from-address, subjects, dedupe,
    and graceful failure when the email backend itself blows up."""

    def setUp(self):
        self.guest = InvitedGuest.objects.create(
            first_name='Alice', last_name='Smith',
            email='alice@example.com', max_guests=2,
        )

    def _payload(self, **overrides):
        base = {
            'household': 'Smith Household',
            'invite_id': self.guest.id,
            'maxGuests': 2,
            'events': [{'id': 'ceremony', 'label': 'Ceremony'}],
            'topEventSelections': ['Ceremony'],
            'guests': [
                {'id': 'g1', 'name': 'Alice Smith', 'type': 'adult', 'events': ['Ceremony']},
            ],
            'contact': {'email': 'alice@example.com', 'phone': ''},
            'notes': '',
            'notify': '',
            'secret': settings.RSVP_SECRET,
            'hp': '',
            'submittedAt': '2026-08-01T12:00:00Z',
        }
        base.update(overrides)
        return base

    def _post(self, payload):
        return self.client.post(
            reverse('wedding:rsvp_submit'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_two_emails_when_addresses_differ(self):
        mail.outbox = []
        r = self._post(self._payload())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        recipients = sorted(addr for m in mail.outbox for addr in m.to)
        self.assertEqual(recipients, ['alice@example.com', 'couple@example.com'])

    def test_one_email_when_contact_matches_notification(self):
        mail.outbox = []
        r = self._post(self._payload(contact={'email': 'couple@example.com'}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['couple@example.com'])

    def test_notification_subject_contains_new_rsvp(self):
        mail.outbox = []
        self._post(self._payload())
        notif = next(m for m in mail.outbox if 'couple@example.com' in m.to)
        self.assertIn('New RSVP', notif.subject)
        self.assertIn('Smith Household', notif.subject)

    def test_confirmation_subject_contains_confirmed(self):
        mail.outbox = []
        self._post(self._payload())
        conf = next(m for m in mail.outbox if 'alice@example.com' in m.to)
        self.assertIn('confirmed', conf.subject.lower())

    def test_emails_use_zacherylong_from_address(self):
        mail.outbox = []
        self._post(self._payload())
        self.assertTrue(mail.outbox)
        for m in mail.outbox:
            self.assertEqual(m.from_email, 'zacherylong@aspiredwebsites.com')

    def test_rsvp_succeeds_when_email_send_fails(self):
        from unittest.mock import patch
        with patch('wedding.views.send_mail', side_effect=Exception('SMTP down')):
            r = self._post(self._payload())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ok'])
        # The submission must still have been saved
        self.assertEqual(RSVPSubmission.objects.filter(invited_guest=self.guest).count(), 1)


class DashboardTests(TestCase):
    USERNAME = 'admin'
    PASSWORD = 'testpass123'

    def setUp(self):
        self.user = User.objects.create_user(self.USERNAME, password=self.PASSWORD)

    def _login(self):
        self.client.login(username=self.USERNAME, password=self.PASSWORD)

    def test_login_page_renders(self):
        r = self.client.get(reverse('wedding:dashboard_login'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Admin Login')

    def test_home_redirects_when_anonymous(self):
        r = self.client.get(reverse('wedding:dashboard_home'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/dashboard/login/', r['Location'])

    def test_home_loads_when_authenticated(self):
        self._login()
        r = self.client.get(reverse('wedding:dashboard_home'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Dashboard')

    def test_guests_loads_when_authenticated(self):
        self._login()
        r = self.client.get(reverse('wedding:dashboard_guests'))
        self.assertEqual(r.status_code, 200)

    def test_add_guest_creates_record(self):
        self._login()
        r = self.client.post(reverse('wedding:dashboard_guest_add'), {
            'first_name': 'Test', 'last_name': 'Guest',
            'email': 'test@example.com', 'phone': '',
            'partner_name': '', 'max_guests': '2', 'notes': '',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(InvitedGuest.objects.filter(first_name='Test', last_name='Guest').exists())

    def test_edit_guest_updates_max_guests(self):
        guest = InvitedGuest.objects.create(first_name='X', last_name='Y', max_guests=1)
        self._login()
        r = self.client.post(reverse('wedding:dashboard_guest_edit', args=[guest.pk]), {
            'first_name': 'X', 'last_name': 'Y',
            'email': '', 'phone': '', 'partner_name': '',
            'max_guests': '5', 'notes': '',
        })
        self.assertEqual(r.status_code, 302)
        guest.refresh_from_db()
        self.assertEqual(guest.max_guests, 5)

    def test_import_csv_protects_existing_rsvped(self):
        existing = InvitedGuest.objects.create(
            first_name='Alice', last_name='Smith',
            email='alice@example.com', max_guests=2,
            rsvped=True, current_guests=2,
        )
        csv_text = (
            'first_name,last_name,email,max_guests\n'
            'Alice,Smith,alice@example.com,4\n'
            'Bob,Jones,bob@example.com,1\n'
        )
        f = SimpleUploadedFile('list.csv', csv_text.encode('utf-8'), content_type='text/csv')
        self._login()
        r = self.client.post(reverse('wedding:dashboard_import'), {'file': f})
        self.assertEqual(r.status_code, 200)
        existing.refresh_from_db()
        self.assertTrue(existing.rsvped, 'rsvped flag must be preserved')
        self.assertEqual(existing.current_guests, 2, 'current_guests must be preserved')
        self.assertEqual(existing.max_guests, 4, 'max_guests must be updated to new value')
        self.assertTrue(InvitedGuest.objects.filter(email='bob@example.com').exists(),
                        'new guest from CSV must be created')

    def test_import_csv_full_name_format(self):
        # "Guest 1 Name" + "Total Number of Guests Invited" spreadsheet format
        csv_text = (
            'Guest 1 Name,Partner Name,Total Number of Guests Invited\n'
            'Carol Doe,Dave Doe,2\n'
        )
        f = SimpleUploadedFile('list.csv', csv_text.encode('utf-8'), content_type='text/csv')
        self._login()
        r = self.client.post(reverse('wedding:dashboard_import'), {'file': f})
        self.assertEqual(r.status_code, 200)
        guest = InvitedGuest.objects.get(first_name='Carol', last_name='Doe')
        self.assertEqual(guest.max_guests, 2)
        self.assertEqual(guest.partner_name, 'Dave Doe')

    def test_rsvps_loads_when_authenticated(self):
        self._login()
        r = self.client.get(reverse('wedding:dashboard_rsvps'))
        self.assertEqual(r.status_code, 200)

    def test_logout_redirects_to_login(self):
        self._login()
        r = self.client.get(reverse('wedding:dashboard_logout'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/dashboard/login/', r['Location'])

    # -- dashboard_rsvp_delete -----------------------------------------

    def _make_submission(self, guest=None):
        if guest is None:
            guest = InvitedGuest.objects.create(
                first_name='Eve', last_name='Adams',
                email='eve@example.com', max_guests=2,
                rsvped=True, current_guests=2,
            )
        return RSVPSubmission.objects.create(
            invited_guest=guest, attending=True,
            email=guest.email or 'eve@example.com', phone='',
        ), guest

    def test_rsvp_delete_requires_authentication(self):
        sub, _ = self._make_submission()
        # Anonymous POST → must redirect to login, not actually delete
        r = self.client.post(reverse('wedding:dashboard_rsvp_delete', args=[sub.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/dashboard/login/', r['Location'])
        self.assertTrue(RSVPSubmission.objects.filter(pk=sub.pk).exists())

    def test_rsvp_delete_post_removes_submission(self):
        sub, _ = self._make_submission()
        self._login()
        r = self.client.post(reverse('wedding:dashboard_rsvp_delete', args=[sub.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(RSVPSubmission.objects.filter(pk=sub.pk).exists())

    def test_rsvp_delete_resets_invited_guest_when_last_submission(self):
        sub, guest = self._make_submission()
        self._login()
        self.client.post(reverse('wedding:dashboard_rsvp_delete', args=[sub.pk]))
        guest.refresh_from_db()
        self.assertFalse(guest.rsvped)
        self.assertEqual(guest.current_guests, 0)

    def test_rsvp_delete_keeps_status_when_other_submissions_remain(self):
        sub1, guest = self._make_submission()
        # Second submission for the same guest stays in place
        RSVPSubmission.objects.create(
            invited_guest=guest, attending=True,
            email=guest.email, phone='',
        )
        self._login()
        self.client.post(reverse('wedding:dashboard_rsvp_delete', args=[sub1.pk]))
        guest.refresh_from_db()
        self.assertTrue(guest.rsvped, 'rsvped flag must stay True while another submission exists')
        self.assertEqual(guest.current_guests, 2)
        self.assertEqual(RSVPSubmission.objects.filter(invited_guest=guest).count(), 1)

    def test_rsvp_delete_redirects_to_rsvps_list(self):
        sub, _ = self._make_submission()
        self._login()
        r = self.client.post(reverse('wedding:dashboard_rsvp_delete', args=[sub.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('wedding:dashboard_rsvps'))


class ImportGuestsCommandTests(TestCase):
    def _write_csv(self, text):
        fd, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_command_creates_guests_from_csv(self):
        path = self._write_csv(
            'first_name,last_name,email,max_guests\n'
            'Alice,Smith,alice@example.com,2\n'
            'Bob,Jones,,3\n'
            'Carol,Doe,carol@example.com,1\n'
        )
        call_command('import_guests', file=path)
        self.assertEqual(InvitedGuest.objects.count(), 3)
        bob = InvitedGuest.objects.get(first_name='Bob', last_name='Jones')
        self.assertIsNone(bob.email, 'blank email must be stored as NULL, not ""')
        self.assertEqual(bob.max_guests, 3)
        carol = InvitedGuest.objects.get(email='carol@example.com')
        self.assertEqual(carol.max_guests, 1)

    def test_command_updates_existing_max_guests_and_skips_unchanged(self):
        InvitedGuest.objects.create(
            first_name='Alice', last_name='Smith',
            email='alice@example.com', max_guests=2,
        )
        InvitedGuest.objects.create(
            first_name='Bob', last_name='Jones',
            email='bob@example.com', max_guests=4,
        )
        path = self._write_csv(
            'first_name,last_name,email,max_guests\n'
            'Alice,Smith,alice@example.com,5\n'   # changed → updated
            'Bob,Jones,bob@example.com,4\n'       # unchanged → skipped
        )
        call_command('import_guests', file=path)
        alice = InvitedGuest.objects.get(email='alice@example.com')
        self.assertEqual(alice.max_guests, 5)
        self.assertEqual(InvitedGuest.objects.count(), 2)
