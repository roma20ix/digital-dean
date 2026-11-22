from functools import wraps
from datetime import date, datetime, time, timedelta

from django.contrib.auth.decorators import login_not_required
from django.db.models import F, Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import AppearanceForm, RequestForm
from .models import (Appearance, Attendance, CourseResult, CourseTask, EmployeeProfile, Exam, Lesson, Notice,
                     StudentProfile, StudentRequest)


@login_not_required
@require_GET
def health(request):
    return HttpResponse("ok\n", content_type="text/plain")


def student_context(user):
    profile = StudentProfile.objects.filter(user=user).first()
    if profile is not None:
        return profile
    return {"full_name": user.get_full_name() or user.get_username(),
            "faculty": "", "program": "", "year": None, "group_name": ""}


def student_lessons(user):
    group = StudentProfile.objects.filter(user=user).values("group_name")
    return Lesson.objects.filter(group_name__in=group)


def student_only(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if getattr(request.user, "employeeprofile", None):
            raise Http404
        return view(request, *args, **kwargs)
    return wrapped


def student_notices(user, now):
    return Notice.objects.filter(
        Q(lesson__isnull=True) | Q(lesson__group_name=F("recipient__group_name")),
        Q(work__isnull=True) | Q(work__week__course__student_id=F("recipient_id"),
                                 category=Notice.Category.DEADLINE, due_at__isnull=False),
        recipient__user=user, created_at__lte=now,
    ).select_related("lesson", "work")


@never_cache
@require_GET
def today(request):
    now = timezone.now()
    employee = getattr(request.user, "employeeprofile", None)
    if employee:
        lessons = Lesson.objects.filter(instructor=employee, ends_at__gt=now)
        return render(request, "employee_today.html", {"upcoming": lessons[:6], "employee": employee})
    notices = student_notices(request.user, now)
    lessons = student_lessons(request.user)
    local_day = timezone.localdate(now)
    start = timezone.make_aware(datetime.combine(local_day, time.min))
    next_deadline = (
        notices.filter(Q(work__isnull=True) | Q(work__status__in=CourseTask.OPEN),
                       category=Notice.Category.DEADLINE, due_at__gte=now)
        .select_related("work__week__course").order_by("due_at", "pk").first()
    )
    return render(request, "today.html", {
        "today_lessons": lessons.filter(starts_at__gte=start, starts_at__lt=start + timedelta(days=1)),
        "student": student_context(request.user),
        "next_lesson": lessons.filter(ends_at__gt=now).first(),
        "next_deadline": next_deadline,
        "latest_request": StudentRequest.objects.filter(owner=request.user).first(),
        "changes": notices.filter(category=Notice.Category.CHANGE),
        "goal_course": CourseResult.objects.filter(
            student__user=request.user, weeks__tasks__notice__recipient__user=request.user,
            weeks__tasks__notice__category=Notice.Category.DEADLINE,
            weeks__tasks__notice__created_at__lte=now,
            weeks__tasks__notice__due_at__isnull=False,
        ).distinct().first(),
    })


@never_cache
@require_http_methods(["GET", "POST"])
def profile(request):
    employee = getattr(request.user, "employeeprofile", None)
    if request.method == "POST":
        form = AppearanceForm(request.POST, request.FILES)
    else:
        form = AppearanceForm()
    if form.is_bound and form.is_valid():
        if form.cleaned_data["photo"]:
            Appearance.objects.update_or_create(user=request.user, defaults={"avatar": form.cleaned_data["photo"]})
        elif form.cleaned_data["remove"]:
            Appearance.objects.filter(user=request.user).update(avatar=None)
        return redirect(reverse("profile") + "?saved=1")
    return render(request, "profile.html", {"student": student_context(request.user),
                                           "employee": employee, "appearance_form": form})


@never_cache
@require_GET
def avatar(request):
    photo = Appearance.objects.filter(user=request.user).values_list("avatar", flat=True).first()
    if not photo:
        raise Http404
    return HttpResponse(bytes(photo), content_type="image/jpeg")


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
    by_date = {start + timedelta(days=i): [] for i in range(length)}
    employee = getattr(request.user, "employeeprofile", None)
    lessons = Lesson.objects.filter(instructor=employee) if employee else student_lessons(request.user)
    lower = timezone.make_aware(datetime.combine(start, time.min))
    upper = lower + timedelta(days=length)
    for lesson in lessons.filter(starts_at__gte=lower, starts_at__lt=upper):
        by_date[timezone.localdate(lesson.starts_at)].append(lesson)
    days = [{"date": day, "lessons": entries} for day, entries in by_date.items()]
    next_teaching_url = None
    if not by_date[selected]:
        tomorrow = timezone.make_aware(datetime.combine(selected + timedelta(days=1), time.min))
        following = lessons.filter(starts_at__gte=tomorrow).first()
        if following:
            next_teaching_url = following.detail_url

    def link(offset):
        return reverse("schedule", query={"date": selected + timedelta(days=offset), "mode": mode})

    return render(request, "schedule.html", {
        "mode": mode, "date": selected.isoformat(), "days": days,
        "lesson_count": sum(len(entries) for entries in by_date.values()),
        "teaching_minutes": sum(int((lesson.ends_at - lesson.starts_at).total_seconds() // 60)
                                for entries in by_date.values() for lesson in entries),
        "prev_url": link(-length), "next_url": link(length), "next_teaching_url": next_teaching_url,
    })


@never_cache
@require_GET
@student_only
def study(request):
    courses = CourseResult.objects.filter(student__user=request.user)
    exams = Exam.objects.filter(course__in=courses, starts_at__gte=timezone.now()).select_related("course")
    return render(request, "study.html", {"courses": courses, "exams": exams})


@never_cache
@require_GET
@student_only
def requests(request):
    return render(request, "requests/list.html", {"items": StudentRequest.objects.filter(owner=request.user)})


@never_cache
@require_http_methods(["GET", "POST"])
@student_only
def request_new(request):
    initial = {"kind": StudentRequest.Kind.APPEAL} if request.GET.get("kind") == "appeal" else {}
    form = RequestForm(request.POST if request.method == "POST" else None, user=request.user, initial=initial)
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        item, _ = StudentRequest.objects.get_or_create(
            owner=request.user, submission_token=data["submission_token"],
            defaults={"kind": data["kind"], "message": data["message"]},
        )
        return redirect(item.detail_url)
    return render(request, "requests/new.html", {"form": form})


@never_cache
@require_GET
@student_only
def request_detail(request, pk):
    item = StudentRequest.objects.filter(owner=request.user, pk=pk).first()
    if item is None:
        return render(request, "requests/detail.html", {"item": None, "history": []}, status=404)
    return render(request, "requests/detail.html", {"item": item, "history": item.history})


@never_cache
@require_GET
@student_only
def inbox(request):
    return render(request, "inbox.html", {"items": student_notices(request.user, timezone.now())})


@never_cache
@require_POST
@student_only
def notice_read(request, pk):
    updated = student_notices(request.user, timezone.now()).filter(pk=pk).update(is_read=True)
    if not updated:
        return HttpResponse("Уведомление не найдено.", status=404, content_type="text/plain; charset=utf-8")
    return redirect("inbox")


def cabinet_header(request):
    if not request.user.is_authenticated:
        return {}
    employee = getattr(request.user, "employeeprofile", None)
    has_avatar = Appearance.objects.filter(user=request.user, avatar__isnull=False).exists()
    student = employee or student_context(request.user)
    name = student.full_name if isinstance(student, (EmployeeProfile, StudentProfile)) else student["full_name"]
    return {"employee_account": employee, "has_avatar": has_avatar,
            "avatar_initials": "".join(part[0] for part in name.split()[:2]).upper(),
            "has_unread": not employee and student_notices(request.user, timezone.now()).filter(is_read=False).exists()}


@never_cache
@require_POST
@student_only
def notice_panel(request):
    notices = student_notices(request.user, timezone.now())
    items = list(notices)
    response = render(request, "components/notice_panel.html", {"items": items})
    notices.filter(pk__in=[item.pk for item in items if not item.is_read]).update(is_read=True)
    return response


@never_cache
@require_GET
@student_only
def attendance(request):
    lessons = student_lessons(request.user).filter(ends_at__lte=timezone.now()).order_by("subject", "-starts_at")
    marks = dict(Attendance.objects.filter(student__user=request.user, lesson__in=lessons)
                 .values_list("lesson_id", "present"))
    courses = {}
    for lesson in lessons:
        course = courses.setdefault(lesson.subject, {"subject": lesson.subject, "entries": [], "present": 0, "marked": 0})
        mark = marks.get(lesson.pk)
        course["entries"].append({"lesson": lesson, "mark": mark})
        if mark is not None:
            course["marked"] += 1
            course["present"] += int(mark)
    totals = {"present": 0, "absent": 0, "unmarked": 0, "marked": 0}
    for course in courses.values():
        course["absent"] = course["marked"] - course["present"]
        course["unmarked"] = len(course["entries"]) - course["marked"]
        if course["marked"]:
            course["percent"] = round(100 * course["present"] / course["marked"])
        for key in totals:
            totals[key] += course[key]
    if totals["marked"]:
        totals["percent"] = round(100 * totals["present"] / totals["marked"])
    return render(request, "attendance.html", {"courses": courses.values(), "totals": totals})


@never_cache
@require_GET
def media(request):
    return render(request, "media.html")
