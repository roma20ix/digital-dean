from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from cabinet import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", views.today, name="today"),
    path("profile/", views.profile, name="profile"),
    path("schedule/", views.schedule, name="schedule"),
    path("attendance/", views.attendance, name="attendance"),
    path("media/", views.media, name="media"),
    path("inbox/panel/", views.notice_panel, name="notice_panel"),
    path("study/", views.study, name="study"),
    path("requests/", views.requests, name="requests"),
    path("requests/new/", views.request_new, name="request_new"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/read/", views.notice_read, name="notice_read"),
]
