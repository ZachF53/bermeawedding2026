from django.urls import path
from . import views

app_name = 'wedding'

urlpatterns = [
    path('', views.home, name='home'),
    path('our-story/', views.our_story, name='our_story'),
    path('events/', views.events, name='events'),
    path('rsvp/', views.rsvp, name='rsvp'),
    path('rsvp/lookup/', views.rsvp_lookup, name='rsvp_lookup'),
    path('rsvp/submit/', views.rsvp_submit, name='rsvp_submit'),
    path('accommodations/', views.accommodations, name='accommodations'),
    path('faq/', views.faq, name='faq'),

    # Dashboard
    path('dashboard/login/',                      views.dashboard_login,        name='dashboard_login'),
    path('dashboard/logout/',                     views.dashboard_logout,       name='dashboard_logout'),
    path('dashboard/',                            views.dashboard_home,         name='dashboard_home'),
    path('dashboard/guests/',                     views.dashboard_guests,       name='dashboard_guests'),
    path('dashboard/guests/add/',                 views.dashboard_guest_add,    name='dashboard_guest_add'),
    path('dashboard/guests/<int:pk>/edit/',       views.dashboard_guest_edit,   name='dashboard_guest_edit'),
    path('dashboard/guests/<int:pk>/delete/',     views.dashboard_guest_delete, name='dashboard_guest_delete'),
    path('dashboard/guests/import/',              views.dashboard_import,       name='dashboard_import'),
    path('dashboard/rsvps/',                      views.dashboard_rsvps,        name='dashboard_rsvps'),
    path('dashboard/rsvps/<int:pk>/',             views.dashboard_rsvp_detail,  name='dashboard_rsvp_detail'),
]
