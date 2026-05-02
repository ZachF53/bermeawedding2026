from django.db import models
from django.utils import timezone


class StoryMoment(models.Model):
    title = models.CharField(max_length=200)
    date = models.CharField(max_length=100, help_text="e.g. 'Summer 2018' or 'June 12, 2022'")
    description = models.TextField()
    image = models.ImageField(upload_to='story/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class Event(models.Model):
    name = models.CharField(max_length=200)
    start = models.DateTimeField()
    location_name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    dress_code = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'start']

    def __str__(self):
        return f"{self.name} — {self.start:%b %d, %Y}"


class CouplePhoto(models.Model):
    caption = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='couple/')
    order = models.PositiveIntegerField(default=0)
    is_hero = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.caption or f"Photo {self.pk}"


class InvitedGuest(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    partner_name = models.CharField(max_length=200, blank=True, default='')
    max_guests = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    rsvped = models.BooleanField(default=False)
    current_guests = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class RSVPSubmission(models.Model):
    invited_guest = models.ForeignKey(
        InvitedGuest,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    attending = models.BooleanField()
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'RSVP submission'

    def __str__(self):
        status = 'Attending' if self.attending else 'Declined'
        return f"{self.invited_guest} — {status}"


class RSVPGuest(models.Model):
    GUEST_TYPE_CHOICES = [('adult', 'Adult'), ('child', 'Child')]

    rsvp = models.ForeignKey(
        RSVPSubmission,
        on_delete=models.CASCADE,
        related_name='guests',
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    guest_type = models.CharField(
        max_length=10,
        choices=GUEST_TYPE_CHOICES,
        default='adult',
    )

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class RSVPEventSelection(models.Model):
    rsvp = models.ForeignKey(
        RSVPSubmission,
        on_delete=models.CASCADE,
        related_name='event_selections',
    )
    event_name = models.CharField(max_length=200)

    class Meta:
        ordering = ['event_name']

    def __str__(self):
        return f"{self.rsvp} — {self.event_name}"


class GuestbookEntry(models.Model):
    name = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(default=timezone.now)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name_plural = 'Guestbook entries'

    def __str__(self):
        return f"{self.name} — {self.submitted_at:%b %d, %Y}"
