from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import RequestForm


@login_not_required
@require_GET
def health(request):
    return HttpResponse("ok\n", content_type="text/plain")


def student_context(user):
    return {"full_name": user.get_full_name() or user.get_username(),
            "faculty": "", "program": "", "year": None, "group_name": ""}


@never_cache
@require_GET
def today(request):
    return render(request, "today.html", {
        "student": student_context(request.user), "next_lesson": None,
        "next_deadline": None, "latest_request": None, "changes": [],
    })


@never_cache
@require_GET
def profile(request):
    return render(request, "profile.html", {"student": student_context(request.user)})


@never_cache
@require_GET
def schedule(request):
    mode = "week" if request.GET.get("mode") == "week" else "day"
    try:
        selected = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        selected = timezone.localdate()
    # Оставляем место для обеих ссылок навигации на границах календаря.
    if selected < date.min + timedelta(days=7) or selected > date.max - timedelta(days=7):
        selected = timezone.localdate()
    length = 7 if mode == "week" else 1
    start = selected - timedelta(days=selected.weekday()) if mode == "week" else selected
    days = [{"date": start + timedelta(days=i), "lessons": []} for i in range(length)]

    def link(offset):
        return reverse("schedule", query={"date": selected + timedelta(days=offset), "mode": mode})

    return render(request, "schedule.html", {
        "mode": mode, "date": selected.isoformat(), "days": days,
        "prev_url": link(-length), "next_url": link(length), "next_teaching_url": None,
    })


@never_cache
@require_GET
def study(request):
    return render(request, "study.html", {"courses": [], "exams": []})


@never_cache
@require_GET
def requests(request):
    return render(request, "requests/list.html", {"items": []})


@never_cache
@require_http_methods(["GET", "POST"])
def request_new(request):
    form = RequestForm(request.POST if request.method == "POST" else None,
                       initial={"submission_token": uuid4()})
    if request.method == "POST":
        form.add_error(None, "Приём заявок ещё не открыт.")
    return render(request, "requests/new.html", {"form": form})


@never_cache
@require_GET
def request_detail(request, pk):
    return render(request, "requests/detail.html", {"item": None, "history": []}, status=404)


@never_cache
@require_GET
def inbox(request):
    return render(request, "inbox.html", {"items": []})


@never_cache
@require_POST
def notice_read(request, pk):
    return HttpResponse("Уведомление не найдено.", status=404, content_type="text/plain; charset=utf-8")
