import csv
import io
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

try:
    import openpyxl
except ImportError:
    openpyxl = None

from .models import (
    StoryMoment,
    Event,
    CouplePhoto,
    InvitedGuest,
    RSVPSubmission,
    RSVPGuest,
    RSVPEventSelection,
)

logger = logging.getLogger(__name__)

DASHBOARD_LOGIN_URL = '/dashboard/login/'


# ----------------------------- Page views -----------------------------

def home(request):
    hero = CouplePhoto.objects.filter(is_hero=True).first()
    photos = CouplePhoto.objects.filter(is_hero=False)[:6]
    return render(request, 'wedding/index.html', {'hero': hero, 'photos': photos})


def our_story(request):
    moments = StoryMoment.objects.all()
    return render(request, 'wedding/our_story.html', {'moments': moments})


def events(request):
    items = Event.objects.all()
    return render(request, 'wedding/events.html', {'events': items})


@ensure_csrf_cookie
def rsvp(request):
    return render(request, 'wedding/rsvp.html', {
        'rsvp_secret': settings.RSVP_SECRET,
    })


def accommodations(request):
    return render(request, 'wedding/accommodations.html')


def faq(request):
    return render(request, 'wedding/faq.html')


# ----------------------------- RSVP API -------------------------------

def _serialize_existing_rsvp(submission):
    return {
        'attending': submission.attending,
        'email': submission.email,
        'phone': submission.phone,
        'notes': submission.notes,
        'guests': [
            {'first_name': g.first_name, 'last_name': g.last_name}
            for g in submission.guests.all()
        ],
        'events': [e.event_name for e in submission.event_selections.all()],
        'submitted_at': submission.submitted_at.isoformat(),
    }


@require_GET
def rsvp_lookup(request):
    email = (request.GET.get('email') or '').strip().lower()
    first_name = (request.GET.get('first_name') or '').strip()
    last_name = (request.GET.get('last_name') or '').strip()

    if not email and not first_name and not last_name:
        return JsonResponse({'found': False})

    if email:
        matches = list(InvitedGuest.objects.filter(email__iexact=email))
    else:
        qs = InvitedGuest.objects.all()
        if first_name:
            qs = qs.filter(first_name__icontains=first_name)
        if last_name:
            qs = qs.filter(last_name__icontains=last_name)
        matches = list(qs)

    if not matches:
        return JsonResponse({'found': False})

    if len(matches) > 1:
        return JsonResponse({
            'found': True,
            'multiple': True,
            'candidates': [
                {
                    'id': g.id,
                    'full_name': f'{g.first_name} {g.last_name}',
                    'email': g.email or '',
                    'max_guests': g.max_guests,
                    'rsvped': 1 if g.rsvped else 0,
                }
                for g in matches
            ],
        })

    g = matches[0]
    last_submission = g.submissions.order_by('-submitted_at').first()
    return JsonResponse({
        'found': True,
        'multiple': False,
        'invite_id': g.id,
        'email': g.email or '',
        'full_name': f'{g.first_name} {g.last_name}',
        'max_guests': g.max_guests,
        'current_guests': g.current_guests,
        'rsvped': 1 if g.rsvped else 0,
        'rsvp': _serialize_existing_rsvp(last_submission) if last_submission else None,
    })


@require_POST
def rsvp_submit(request):
    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    if (payload.get('hp') or '').strip():
        return JsonResponse({'ok': False, 'error': 'Spam detected'}, status=400)

    if payload.get('secret') != settings.RSVP_SECRET:
        return JsonResponse({'ok': False, 'error': 'Invalid request'}, status=403)

    guests = payload.get('guests') or []
    if not isinstance(guests, list) or not guests:
        return JsonResponse({'ok': False, 'error': 'No guests provided'}, status=422)

    contact = payload.get('contact') or {}
    contact_email = (contact.get('email') or '').strip()
    if not contact_email:
        return JsonResponse({'ok': False, 'error': 'Contact email required'}, status=422)

    invited = None
    invite_id = payload.get('invite_id')
    if invite_id:
        invited = InvitedGuest.objects.filter(pk=invite_id).first()
    if not invited:
        invited = InvitedGuest.objects.filter(email__iexact=contact_email).first()
    if not invited:
        return JsonResponse({'ok': False, 'error': 'Invitation not found'}, status=404)

    contact_phone = (contact.get('phone') or '').strip()
    notes = (payload.get('notes') or '').strip()
    top_events = payload.get('topEventSelections') or []

    try:
        with transaction.atomic():
            submission = RSVPSubmission.objects.create(
                invited_guest=invited,
                attending=True,
                email=contact_email,
                phone=contact_phone,
                notes=notes,
            )

            stored_guests = 0
            for g in guests:
                name = (g.get('name') or '').strip() if isinstance(g, dict) else ''
                if not name:
                    continue
                parts = name.split(None, 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ''
                RSVPGuest.objects.create(
                    rsvp=submission,
                    first_name=first,
                    last_name=last,
                )
                stored_guests += 1

            for event_name in top_events:
                evt = str(event_name).strip()
                if evt:
                    RSVPEventSelection.objects.create(rsvp=submission, event_name=evt)

            invited.rsvped = True
            invited.current_guests = stored_guests
            invited.save(update_fields=['rsvped', 'current_guests'])
    except Exception:
        logger.exception("RSVP submit failed")
        return JsonResponse({'ok': False, 'error': 'Could not save RSVP'}, status=500)

    # Email is best-effort — never let it break the saved-RSVP response.
    try:
        _send_rsvp_emails(submission, payload)
    except Exception as e:
        logger.exception("RSVP email send failed: %s", e)

    return JsonResponse({'ok': True, 'id': submission.id})


def _send_rsvp_emails(submission, payload):
    invited = submission.invited_guest
    contact = payload.get('contact') or {}
    contact_email = (contact.get('email') or '').strip()
    contact_phone = (contact.get('phone') or '').strip()
    notes = (payload.get('notes') or '').strip()
    household_name = (payload.get('household') or '').strip() or f'{invited.first_name} {invited.last_name}'
    submitted_at = (payload.get('submittedAt') or '').strip() or submission.submitted_at.isoformat()
    guests = payload.get('guests') or []
    top_events = payload.get('topEventSelections') or []

    # Walk the party once: build the per-guest summary lines and capture the
    # first guest's first name (used to greet the confirmation recipient).
    guest_lines = []
    first_guest_name = ''
    for g in guests:
        if not isinstance(g, dict):
            continue
        name = (g.get('name') or '').strip()
        if not name:
            continue
        if not first_guest_name:
            first_guest_name = name.split()[0]
        gtype = (g.get('type') or '').strip()
        gevents = ', '.join(g.get('events') or [])
        line = f"  - {name}"
        if gtype:
            line += f" ({gtype})"
        if gevents:
            line += f" — events: {gevents}"
        guest_lines.append(line)
    if not first_guest_name:
        first_guest_name = invited.first_name

    summary_text = (
        f"Household: {household_name}\n\n"
        f"Guests:\n"
        + ('\n'.join(guest_lines) if guest_lines else '  (none)')
        + "\n\n"
        f"Top-level events: {', '.join(top_events) or '(none)'}\n\n"
        f"Contact:\n"
        f"  Email: {contact_email}\n"
        f"  Phone: {contact_phone or '—'}\n\n"
        f"Notes:\n{notes or '—'}\n"
    )

    notify_addr = getattr(settings, 'NOTIFICATION_EMAIL', '')

    # 1. Notification to the wedding couple
    if notify_addr:
        notification_text = (
            f"New RSVP received!\n\n"
            f"Submitted: {submitted_at}\n\n"
            f"{summary_text}\n"
            f"---\n"
            f"Sent from bermeawedding2026.com\n"
        )
        try:
            send_mail(
                subject='New RSVP — ' + household_name,
                message=notification_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notify_addr],
                fail_silently=False,
            )
        except Exception as e:
            logger.exception("Notification email failed: %s", e)

    # 2. Confirmation to guest (only if their address differs from the couple's)
    if contact_email and contact_email != notify_addr:
        confirmation_text = (
            f"Hi {first_guest_name},\n\n"
            f"Thank you for your RSVP! We're so excited to celebrate with you.\n\n"
            f"Here's a summary of your RSVP:\n\n"
            f"{summary_text}\n"
            f"Wedding Details:\n"
            f"  Date: Saturday, September 5, 2026\n"
            f"  Time: Ceremony at 5:30 PM | Doors open at 5:00 PM\n"
            f"  Venue: The Skyline\n"
            f"  Address: 707 Dawson St, San Antonio, TX 78202\n\n"
            f"Dress Code: Semi-Formal (required)\n"
            f"Hashtag: #BermeaEverAfter\n\n"
            f"If you need to make any changes, please contact us at:\n"
            f"bermeawedding@outlook.com\n\n"
            f"We can't wait to see you!\n\n"
            f"With love,\n"
            f"Brian & Aisha\n"
        )
        try:
            send_mail(
                subject='Your RSVP is confirmed — Brian & Aisha Wedding',
                message=confirmation_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contact_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.exception("Confirmation email failed: %s", e)


# ----------------------------- Dashboard ------------------------------

def dashboard_login(request):
    if request.user.is_authenticated:
        return redirect('wedding:dashboard_home')
    error = ''
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('wedding:dashboard_home')
        error = 'Invalid username or password.'
    return render(request, 'dashboard/login.html', {'error': error})


def dashboard_logout(request):
    logout(request)
    return redirect('wedding:dashboard_login')


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_home(request):
    invited_total  = InvitedGuest.objects.aggregate(s=Sum('max_guests'))['s'] or 0
    households     = InvitedGuest.objects.count()
    rsvped         = InvitedGuest.objects.filter(rsvped=True).count()
    attending      = InvitedGuest.objects.filter(rsvped=True).aggregate(s=Sum('current_guests'))['s'] or 0
    not_responded  = InvitedGuest.objects.filter(rsvped=False).count()
    return render(request, 'dashboard/home.html', {
        'invited_total': invited_total,
        'households': households,
        'rsvped': rsvped,
        'attending': attending,
        'not_responded': not_responded,
        'rsvp_deadline': 'July 24, 2026',
        'active_page': 'home',
    })


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_guests(request):
    qs = InvitedGuest.objects.all().order_by('last_name', 'first_name')
    search = (request.GET.get('search') or '').strip()
    rsvped_filter = (request.GET.get('rsvped') or '').strip()
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    if rsvped_filter == 'yes':
        qs = qs.filter(rsvped=True)
    elif rsvped_filter == 'no':
        qs = qs.filter(rsvped=False)
    guests = list(qs)
    return render(request, 'dashboard/guests.html', {
        'guests': guests,
        'search': search,
        'rsvped_filter': rsvped_filter,
        'total': len(guests),
        'active_page': 'guests',
    })


def _save_guest_from_form(post, guest=None):
    errors = {}
    first_name   = (post.get('first_name') or '').strip()
    last_name    = (post.get('last_name') or '').strip()
    email        = (post.get('email') or '').strip()
    phone        = (post.get('phone') or '').strip()
    partner_name = (post.get('partner_name') or '').strip()
    notes        = (post.get('notes') or '').strip()
    try:
        max_guests = int(post.get('max_guests') or 0)
    except (TypeError, ValueError):
        max_guests = 0
    if not first_name:
        errors['first_name'] = 'First name is required.'
    if not last_name:
        errors['last_name'] = 'Last name is required.'
    if max_guests < 1:
        errors['max_guests'] = 'Max guests must be at least 1.'
    if errors:
        return False, errors, guest
    if guest is None:
        guest = InvitedGuest()
    guest.first_name   = first_name
    guest.last_name    = last_name
    guest.email        = email or None
    guest.phone        = phone
    guest.partner_name = partner_name
    guest.max_guests   = max_guests
    guest.notes        = notes
    try:
        guest.save()
    except Exception as e:
        errors['__all__'] = str(e)
        return False, errors, guest
    return True, {}, guest


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_guest_add(request):
    if request.method == 'POST':
        ok, errors, guest = _save_guest_from_form(request.POST)
        if ok:
            messages.success(request, 'Guest "%s %s" added.' % (guest.first_name, guest.last_name))
            return redirect('wedding:dashboard_guests')
        return render(request, 'dashboard/guest_form.html', {
            'guest': None, 'errors': errors, 'data': request.POST,
            'mode': 'add', 'active_page': 'add',
        })
    return render(request, 'dashboard/guest_form.html', {
        'guest': None, 'data': {'max_guests': 2},
        'mode': 'add', 'active_page': 'add',
    })


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_guest_edit(request, pk):
    guest = get_object_or_404(InvitedGuest, pk=pk)
    if request.method == 'POST':
        ok, errors, _ = _save_guest_from_form(request.POST, guest=guest)
        if ok:
            messages.success(request, 'Guest "%s %s" updated.' % (guest.first_name, guest.last_name))
            return redirect('wedding:dashboard_guests')
        return render(request, 'dashboard/guest_form.html', {
            'guest': guest, 'errors': errors, 'data': request.POST,
            'mode': 'edit', 'active_page': 'guests',
        })
    return render(request, 'dashboard/guest_form.html', {
        'guest': guest,
        'data': {
            'first_name':   guest.first_name,
            'last_name':    guest.last_name,
            'email':        guest.email or '',
            'phone':        guest.phone or '',
            'partner_name': guest.partner_name or '',
            'max_guests':   guest.max_guests,
            'notes':        guest.notes or '',
        },
        'mode': 'edit', 'active_page': 'guests',
    })


@require_POST
@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_guest_delete(request, pk):
    guest = get_object_or_404(InvitedGuest, pk=pk)
    name = '%s %s' % (guest.first_name, guest.last_name)
    # RSVPSubmission(s) cascade-delete via FK on_delete=CASCADE
    guest.delete()
    messages.success(request, 'Guest "%s" deleted.' % name)
    return redirect('wedding:dashboard_guests')


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_import(request):
    context = {'active_page': 'import'}
    if request.method == 'POST':
        upload = request.FILES.get('file')
        if not upload:
            context['error'] = 'Please choose a file to upload.'
        else:
            context['results'] = _import_guests_file(upload)
    return render(request, 'dashboard/import.html', context)


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_rsvps(request):
    qs = (
        RSVPSubmission.objects
        .select_related('invited_guest')
        .prefetch_related('guests', 'event_selections')
        .order_by('-submitted_at')
    )
    search = (request.GET.get('search') or '').strip()
    if search:
        qs = qs.filter(
            Q(invited_guest__first_name__icontains=search) |
            Q(invited_guest__last_name__icontains=search) |
            Q(email__icontains=search)
        )
    rsvps = list(qs)
    return render(request, 'dashboard/rsvps.html', {
        'rsvps': rsvps,
        'search': search,
        'total': len(rsvps),
        'active_page': 'rsvps',
    })


@login_required(login_url=DASHBOARD_LOGIN_URL)
def dashboard_rsvp_detail(request, pk):
    rsvp = get_object_or_404(
        RSVPSubmission.objects
            .select_related('invited_guest')
            .prefetch_related('guests', 'event_selections'),
        pk=pk,
    )
    return render(request, 'dashboard/rsvp_detail.html', {
        'rsvp': rsvp,
        'active_page': 'rsvps',
    })


# ----------------------------- Import helpers -------------------------

_COLUMN_ALIASES = {
    'first_name':         ['first_name', 'firstname', 'first', 'guest1firstname'],
    'last_name':          ['last_name', 'lastname', 'last', 'guest1lastname'],
    'full_name':          ['full_name', 'fullname', 'name', 'guest1name', 'guest_1_name'],
    'email':              ['email', 'emailaddress', 'guestemail'],
    'phone':              ['phone', 'phonenumber', 'mobile'],
    'max_guests':         ['max_guests', 'maxguests', 'totalnumberofguestsinvited',
                           'totalguests', 'guestcount', 'invited'],
    'partner_first_name': ['partner_first_name', 'partnerfirstname'],
    'partner_last_name':  ['partner_last_name', 'partnerlastname'],
    'partner_full_name':  ['partner_full_name', 'partnerfullname', 'partnername'],
    'notes':              ['notes', 'note'],
}


def _norm_key(s):
    return ''.join(c for c in str(s).lower() if c.isalnum() or c == '_')


def _read_rows(uploaded):
    name = (uploaded.name or '').lower()
    if name.endswith('.csv'):
        text = uploaded.read().decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        return list(reader), None

    if name.endswith('.xlsx'):
        if openpyxl is None:
            return [], 'openpyxl is not installed; cannot read .xlsx files.'
        try:
            wb = openpyxl.load_workbook(uploaded, data_only=True, read_only=True)
        except Exception as e:
            return [], 'Failed to open workbook: %s' % e
        ws = wb.active
        iter_rows = ws.iter_rows(values_only=True)
        try:
            headers = ['' if h is None else str(h).strip() for h in next(iter_rows)]
        except StopIteration:
            return [], 'Empty file.'
        rows = []
        for row in iter_rows:
            d = {}
            for i, h in enumerate(headers):
                d[h] = row[i] if i < len(row) else None
            rows.append(d)
        return rows, None

    return [], 'Unsupported file type. Use .csv or .xlsx.'


def _normalize_import_row(row):
    by_norm = {}
    for k, v in row.items():
        if k is None:
            continue
        by_norm[_norm_key(k)] = v if v is not None else ''

    def get(canonical):
        for alias in _COLUMN_ALIASES.get(canonical, [canonical]):
            n = _norm_key(alias)
            if n in by_norm:
                val = by_norm[n]
                if val is None:
                    return ''
                return str(val).strip()
        return ''

    first_name = get('first_name')
    last_name  = get('last_name')
    full_name  = get('full_name')
    if not first_name and not last_name and full_name:
        parts = full_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''
    if not first_name and not last_name:
        return None  # empty row

    email = get('email')
    phone = get('phone')

    raw = get('max_guests')
    try:
        max_guests = int(float(raw)) if raw else None
    except (TypeError, ValueError):
        max_guests = None

    partner_full = get('partner_full_name')
    if not partner_full:
        pf = get('partner_first_name')
        pl = get('partner_last_name')
        partner_full = (pf + ' ' + pl).strip()

    if max_guests is None:
        max_guests = 2 if partner_full else 1

    return {
        'first_name':   first_name,
        'last_name':    last_name,
        'email':        email,
        'phone':        phone,
        'max_guests':   max_guests,
        'partner_name': partner_full,
        'notes':        get('notes'),
    }


def _apply_import_row(data):
    existing = None
    if data.get('email'):
        existing = InvitedGuest.objects.filter(email__iexact=data['email']).first()
    if not existing:
        existing = InvitedGuest.objects.filter(
            first_name__iexact=data['first_name'],
            last_name__iexact=data['last_name'],
        ).first()

    if existing:
        changed = False
        if data.get('max_guests') and data['max_guests'] != existing.max_guests:
            existing.max_guests = data['max_guests']
            changed = True
        if data.get('email') and not existing.email:
            existing.email = data['email']
            changed = True
        if data.get('phone') and not existing.phone:
            existing.phone = data['phone']
            changed = True
        if data.get('partner_name') and not existing.partner_name:
            existing.partner_name = data['partner_name']
            changed = True
        if changed:
            existing.save()
            return 'updated'
        return 'skipped'

    InvitedGuest.objects.create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=(data.get('email') or None),
        phone=data.get('phone', ''),
        partner_name=data.get('partner_name', ''),
        max_guests=data.get('max_guests', 1) or 1,
        notes=data.get('notes', ''),
    )
    return 'created'


def _import_guests_file(uploaded):
    results = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': []}
    rows, err = _read_rows(uploaded)
    if err:
        results['errors'].append(err)
        return results
    for line_no, row in enumerate(rows, start=2):
        try:
            normalized = _normalize_import_row(row)
        except Exception as e:
            results['errors'].append('Row %d: %s' % (line_no, e))
            continue
        if not normalized:
            results['skipped'] += 1
            continue
        try:
            action = _apply_import_row(normalized)
        except Exception as e:
            results['errors'].append('Row %d (%s %s): %s' % (
                line_no, normalized.get('first_name', ''), normalized.get('last_name', ''), e))
            continue
        results[action] += 1
    return results
