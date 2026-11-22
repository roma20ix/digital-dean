from datetime import timedelta

from django import forms
from django.db import transaction
from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from .models import CourseMessage, CourseResult, CourseTask, CourseWeek, Notice, StudentProfile
from .views import student_only


def my_courses(user):
    return CourseResult.objects.filter(student__user=user).select_related("student")


def my_tasks(user):
    return CourseTask.objects.filter(
        week__course__student__user=user, notice__recipient_id=F("week__course__student_id"),
        notice__category=Notice.Category.DEADLINE, notice__created_at__lte=timezone.now(), notice__due_at__isnull=False,
    ).select_related("week__course", "notice").order_by("notice__due_at", "pk")


@never_cache
@require_GET
@student_only
def catalog(request):
    category = request.GET.get("category", "")
    courses = my_courses(request.user)
    if category:
        courses = courses.filter(category=category)
    return render(request, "learning/catalog.html", {
        "courses": courses, "category": category, "categories": CourseResult.Category.choices,
    })


@never_cache
@require_GET
@student_only
def course_detail(request, pk):
    course = get_object_or_404(my_courses(request.user), pk=pk)
    scoped = my_tasks(request.user).filter(week__course=course)
    weeks = list(course.weeks.prefetch_related(Prefetch("tasks", queryset=scoped)))
    tasks = [task for week in weeks for task in week.tasks.all()]
    now = timezone.now()
    upcoming = [task for task in tasks if task.is_open and task.notice.due_at >= now]
    points = sum(task.score or 0 for task in tasks)
    maximum = sum(task.max_score for task in tasks)
    return render(request, "learning/course.html", {
        "course": course, "weeks": weeks, "recordings": [week for week in weeks if week.recording],
        "tab": request.GET.get("tab"), "points": points, "scaled": 10 * points / maximum if maximum else None,
        "remaining": sum(task.max_score for task in tasks if task.score is None),
        "maximum": maximum, "now": now,
        "nearest": min(upcoming, key=lambda task: task.notice.due_at, default=None),
    })


@never_cache
@require_GET
@student_only
def material(request, pk):
    week = get_object_or_404(CourseWeek.objects.select_related("course"), course__student__user=request.user, pk=pk)
    return render(request, "learning/material.html", {"week": week, "course": week.course})


@never_cache
@require_GET
@student_only
def task_list(request):
    courses = list(my_courses(request.user))
    course_ids = request.GET.getlist("course")
    statuses = request.GET.getlist("status")
    tasks = my_tasks(request.user)
    if course_ids:
        tasks = tasks.filter(week__course_id__in=[c.pk for c in courses if str(c.pk) in course_ids])
    if statuses:
        tasks = tasks.filter(status__in=statuses)
    now = timezone.now()
    today = timezone.localdate(now)
    monday = today - timedelta(days=today.weekday())
    groups = {"Ранее": [], "Эта неделя": [], "Далее": []}
    for task in tasks:
        day = timezone.localdate(task.notice.due_at)
        group = "Эта неделя"
        if day < monday:
            group = "Ранее"
        elif day >= monday + timedelta(days=7):
            group = "Далее"
        groups[group].append(task)
    return render(request, "learning/tasks.html", {
        "groups": {label: rows for label, rows in groups.items() if rows},
        "course_choices": [(c.pk, c.title, str(c.pk) in course_ids) for c in courses],
        "statuses": CourseTask.Status.choices, "selected_statuses": statuses,
        "filtered": bool(course_ids or statuses), "now": now,
        "student": getattr(request.user, "studentprofile", None),
    })


class AnswerForm(forms.Form):
    answer = forms.CharField(label="Ваше решение", max_length=8000, widget=forms.Textarea)


class RatingForm(forms.Form):
    rating = forms.TypedChoiceField(label="Оценка материала", choices=[(i, str(i)) for i in range(1, 6)], coerce=int)


def extend_deadline(task, student, now):
    unavailable = "Перенос доступен один раз до окончания срока открытой работы."
    if task.notice.due_at <= now:
        return unavailable
    with transaction.atomic():
        claimed = CourseTask.objects.filter(pk=task.pk, status__in=CourseTask.OPEN, extended=False).update(extended=True)
        if not claimed:
            return unavailable
        if not StudentProfile.objects.filter(pk=student.pk, late_days__gt=0).update(late_days=F("late_days") - 1):
            transaction.set_rollback(True)
            return "Дни переноса закончились."
        Notice.objects.filter(pk=task.notice_id).update(due_at=F("due_at") + timedelta(days=1))
    return ""


@never_cache
@require_http_methods(["GET", "POST"])
@student_only
def task_detail(request, pk):
    task = get_object_or_404(my_tasks(request.user), pk=pk)
    course = task.week.course
    student = course.student
    answer_form = AnswerForm(initial={"answer": task.answer})
    rating_form = RatingForm(initial={"rating": task.rating})
    now = timezone.now()
    error = ""
    if request.method == "POST":
        action = request.POST.get("action")
        own = CourseTask.objects.filter(pk=task.pk)
        if action == "extend":
            error = extend_deadline(task, student, now)
        elif action == "rate":
            rating_form = RatingForm(request.POST)
            if rating_form.is_valid():
                own.update(rating=rating_form.cleaned_data["rating"])
            else:
                error = "Выберите оценку материала от 1 до 5."
        elif action == "start":
            own.filter(status=CourseTask.Status.ASSIGNED).update(status=CourseTask.Status.STARTED)
        elif action in ("save", "submit"):
            answer_form = AnswerForm(request.POST)
            if not task.is_open:
                error = "Решение уже передано на проверку."
            elif answer_form.is_valid():
                fields = {"answer": answer_form.cleaned_data["answer"], "status": CourseTask.Status.DRAFT}
                if action == "submit":
                    fields.update(status=CourseTask.Status.REVIEW, submitted_at=now)
                if not own.filter(status__in=CourseTask.OPEN).update(**fields):
                    error = "Статус работы изменился. Обновите страницу."
            else:
                error = "Проверьте текст решения."
        else:
            error = "Неизвестное действие."
        if not error:
            return redirect(task.detail_url)
    return render(request, "learning/task.html", {
        "task": task, "course": course, "answer_form": answer_form, "rating_form": rating_form,
        "error": error, "student": student, "now": now,
    })


class MessageForm(forms.Form):
    body = forms.CharField(label="Сообщение группе", max_length=1500, widget=forms.Textarea(attrs={"rows": 3}))


@never_cache
@require_http_methods(["GET", "POST"])
@student_only
def course_chat(request, pk):
    course = get_object_or_404(my_courses(request.user), pk=pk)
    room = {"group_name": course.student.group_name, "course_title": course.title}
    form = MessageForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        CourseMessage.objects.create(**room, author=course.student, body=form.cleaned_data["body"])
        return redirect(reverse("course_chat", args=[pk]) + "#latest")
    messages = CourseMessage.objects.filter(**room).select_related("author")
    return render(request, "learning/chat.html", {"course": course, "messages_list": messages, "form": form})
