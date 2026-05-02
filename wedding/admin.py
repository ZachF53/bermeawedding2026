import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import (
    StoryMoment,
    Event,
    CouplePhoto,
    InvitedGuest,
    RSVPSubmission,
    RSVPGuest,
    RSVPEventSelection,
    GuestbookEntry,
)


@admin.action(description="Export selected guests as CSV")
def export_guests_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="guest_list.csv"'
    writer = csv.writer(response)
    writer.writerow(['First Name', 'Last Name', 'Email', 'Max Guests', 'Notes', 'Created'])
    for guest in queryset:
        writer.writerow([
            guest.first_name,
            guest.last_name,
            guest.email or '',
            guest.max_guests,
            guest.notes,
            guest.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@admin.action(description="Export selected RSVPs as CSV")
def export_rsvps_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rsvps.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Invited Guest', 'Invited Email', 'Attending',
        'Contact Email', 'Phone',
        'Party Members', 'Events', 'Notes', 'Submitted',
    ])
    qs = queryset.select_related('invited_guest').prefetch_related('guests', 'event_selections')
    for rsvp in qs:
        party = '; '.join(f"{g.first_name} {g.last_name}" for g in rsvp.guests.all())
        events = '; '.join(e.event_name for e in rsvp.event_selections.all())
        writer.writerow([
            f"{rsvp.invited_guest.first_name} {rsvp.invited_guest.last_name}",
            rsvp.invited_guest.email or '',
            'Yes' if rsvp.attending else 'No',
            rsvp.email,
            rsvp.phone,
            party,
            events,
            rsvp.notes,
            rsvp.submitted_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


class RSVPGuestInline(admin.TabularInline):
    model = RSVPGuest
    extra = 0


class RSVPEventSelectionInline(admin.TabularInline):
    model = RSVPEventSelection
    extra = 0


@admin.register(InvitedGuest)
class InvitedGuestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'max_guests', 'created_at')
    list_filter = ('max_guests', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'notes')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('created_at',)
    actions = [export_guests_csv]


@admin.register(RSVPSubmission)
class RSVPSubmissionAdmin(admin.ModelAdmin):
    list_display = ('invited_guest', 'attending', 'email', 'phone', 'submitted_at')
    list_filter = ('attending', 'submitted_at')
    search_fields = (
        'invited_guest__first_name',
        'invited_guest__last_name',
        'invited_guest__email',
        'email',
        'phone',
        'notes',
    )
    ordering = ('-submitted_at',)
    readonly_fields = ('submitted_at',)
    inlines = [RSVPGuestInline, RSVPEventSelectionInline]
    actions = [export_rsvps_csv]


@admin.register(RSVPGuest)
class RSVPGuestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'rsvp')
    search_fields = ('first_name', 'last_name', 'rsvp__invited_guest__last_name')
    list_filter = ('rsvp__attending',)


@admin.register(RSVPEventSelection)
class RSVPEventSelectionAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'rsvp')
    list_filter = ('event_name',)
    search_fields = ('event_name', 'rsvp__invited_guest__last_name')


@admin.register(StoryMoment)
class StoryMomentAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'order')
    list_editable = ('order',)
    search_fields = ('title', 'description')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'start', 'location_name', 'order')
    list_editable = ('order',)
    list_filter = ('start',)
    search_fields = ('name', 'location_name')


@admin.register(CouplePhoto)
class CouplePhotoAdmin(admin.ModelAdmin):
    list_display = ('caption', 'is_hero', 'order')
    list_editable = ('is_hero', 'order')


@admin.register(GuestbookEntry)
class GuestbookEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'submitted_at', 'approved')
    list_filter = ('approved', 'submitted_at')
    list_editable = ('approved',)
    search_fields = ('name', 'message')
