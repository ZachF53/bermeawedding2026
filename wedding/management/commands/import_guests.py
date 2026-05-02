import csv

from django.core.management.base import BaseCommand

from wedding.models import InvitedGuest


class Command(BaseCommand):
    help = 'Import guests from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to CSV file')

    def handle(self, *args, **options):
        filepath = options['file']
        created = updated = skipped = 0

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                first = (row.get('first_name') or '').strip()
                last  = (row.get('last_name') or '').strip()
                email = (row.get('email') or '').strip()
                try:
                    max_g = max(1, int(float(row.get('max_guests') or 2)))
                except (TypeError, ValueError):
                    max_g = 2

                if not first:
                    skipped += 1
                    continue

                existing = None
                if email:
                    existing = InvitedGuest.objects.filter(email__iexact=email).first()
                if not existing:
                    existing = InvitedGuest.objects.filter(
                        first_name__iexact=first,
                        last_name__iexact=last,
                    ).first()

                if existing:
                    changed = False
                    if existing.max_guests != max_g:
                        existing.max_guests = max_g
                        changed = True
                    if email and not existing.email:
                        existing.email = email
                        changed = True
                    if changed:
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                else:
                    InvitedGuest.objects.create(
                        first_name=first,
                        last_name=last,
                        email=(email or None),
                        max_guests=max_g,
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            'Done: %d created, %d updated, %d skipped' % (created, updated, skipped)
        ))
