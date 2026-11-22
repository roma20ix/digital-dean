from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from cabinet import learning, views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", views.today, name="today"),
    path("profile/avatar/", views.avatar, name="avatar"),
    path("profile/", views.profile, name="profile"),
    path("schedule/", views.schedule, name="schedule"),
    path("attendance/", views.attendance, name="attendance"),
    path("media/", views.media, name="media"),
    path("inbox/panel/", views.notice_panel, name="notice_panel"),
    path("study/", views.study, name="study"),
    path("study/courses/", learning.catalog, name="course_catalog"),
    path("study/courses/<int:pk>/", learning.course_detail, name="course_detail"),
    path("study/courses/<int:pk>/chat/", learning.course_chat, name="course_chat"),
    path("study/materials/<int:pk>/", learning.material, name="course_material"),
    path("study/tasks/", learning.task_list, name="task_list"),
    path("study/tasks/<int:pk>/", learning.task_detail, name="task_detail"),
    path("requests/", views.requests, name="requests"),
    path("requests/new/", views.request_new, name="request_new"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("inbox/", views.inbox, name="inbox"),
    path("inbox/<int:pk>/read/", views.notice_read, name="notice_read"),
]
