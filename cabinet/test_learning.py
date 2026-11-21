import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import StringIO
from secrets import token_urlsafe
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .models import CourseMessage, CourseResult, CourseTask, CourseWeek, Notice, StudentProfile


NOW = datetime(2026, 11, 20, 9, tzinfo=ZoneInfo("Europe/Moscow"))


PASSWORDS = {key: token_urlsafe() for key in (
    "DEMO_STUDENT_A_PASSWORD", "DEMO_STUDENT_B_PASSWORD", "DEMO_TEACHER_PASSWORD")}


def seed():
    with patch.dict(os.environ, PASSWORDS):
        call_command("seed_demo", stdout=StringIO())


class LearningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()
        cls.a, cls.b = list(StudentProfile.objects.order_by("user__username"))
        cls.teacher = get_user_model().objects.get(username="teacher_a")

    def setUp(self):
        self.clock = self.enterContext(patch("django.utils.timezone.now", return_value=NOW))
        self.client.force_login(self.a.user)

    def test_journey_and_gradebook_for_both_students(self):
        for student, topic, points in [(self.a, "Линейная алгебра", 9), (self.b, "Гражданское право", 8)]:
            self.client.force_login(student.user)
            nearest = self.client.get("/").context["next_deadline"]
            task = self.client.get(nearest.target_url).context["task"]
            course = task.week.course
            self.assertEqual((course.title, course.student), (topic, student))
            page = self.client.get(reverse("course_detail", args=[course.pk]))
            self.assertEqual((page.context["points"], page.context["remaining"], page.context["maximum"]),
                             (points, 30, 40))
            self.assertEqual(page.context["nearest"], task)
            self.assertContains(page, task.detail_url)
            self.assertContains(self.client.get(reverse("study")), f'id="course-{course.pk}"')
            self.assertContains(self.client.get(reverse("course_material", args=[task.week_id])), task.week.material)
            self.assertContains(self.client.get(reverse("inbox")), task.detail_url)
            self.assertContains(self.client.post(reverse("notice_panel")), task.detail_url)
            self.assertContains(self.client.get(reverse("task_list")), task.detail_url)
            catalog = self.client.get(reverse("course_catalog"), {"category": "elective"})
            self.assertEqual([c.category for c in catalog.context["courses"]], ["elective"])

    def test_home_shows_exam_registration_when_it_is_due_next(self):
        self.clock.return_value = NOW.replace(day=29)
        home = self.client.get("/")
        self.assertContains(home, "Запись на экзамен")
        self.assertContains(home, "Подтвердить до 30 ноября, 18:00 МСК")
        self.assertNotContains(home, "Ближайшее домашнее задание")
        self.assertContains(self.client.get(home.context["next_deadline"].target_url), "Запись на экзамен · Неделя")

    def test_draft_submit_validation_and_reseed(self):
        task = self.client.get("/").context["next_deadline"].work
        url = task.detail_url
        self.assertContains(self.client.post(url, {"action": "submit", "answer": "  "}), "Проверьте текст")
        self.assertRedirects(self.client.post(url, {"action": "start"}), url)
        self.assertRedirects(self.client.post(url, {"action": "save", "answer": "Промежуточный вывод"}), url)
        self.assertContains(self.client.get(url), "Промежуточный вывод")
        self.assertRedirects(self.client.post(url, {"action": "submit", "answer": "Мой итог"}), url)
        self.assertContains(self.client.post(url, {"action": "submit", "answer": "Другой текст"}), "уже передано")
        self.assertRedirects(self.client.post(url, {"action": "rate", "rating": 4}), url)
        counts = [model.objects.count() for model in (CourseWeek, CourseTask, Notice)]
        seed()
        self.assertEqual(counts, [model.objects.count() for model in (CourseWeek, CourseTask, Notice)])
        self.client.logout()
        self.client.force_login(self.a.user)
        task.refresh_from_db()
        self.assertEqual((task.status, task.answer, task.rating, task.submitted_at),
                         ("review", "Мой итог", 4, NOW))
        self.assertNotEqual(self.client.get("/").context["next_deadline"].pk, task.notice_id)
        self.assertContains(self.client.get(url), "На проверке")

    def test_extension_shared_date_and_remaining_allowance(self):
        notice = self.client.get("/").context["next_deadline"]
        url = notice.work.detail_url
        expected = notice.due_at + timedelta(days=1)
        self.assertRedirects(self.client.post(url, {"action": "extend"}), url)
        self.assertContains(self.client.post(url, {"action": "extend"}), "доступен один раз")
        seed()
        self.a.refresh_from_db()
        notice.refresh_from_db()
        self.assertEqual((notice.due_at, self.a.late_days), (expected, 2))
        self.assertEqual(self.client.get("/").context["next_deadline"].due_at, expected)
        self.assertEqual(self.client.get(url).context["task"].notice.due_at, expected)
        self.a.late_days = 0
        self.a.save(update_fields=["late_days"])
        other = CourseTask.objects.get(week__course__student=self.a, status="started")
        self.assertContains(self.client.post(other.detail_url, {"action": "extend"}), "закончились")
        other.refresh_from_db()
        self.assertFalse(other.extended)
        self.clock.return_value = expected + timedelta(days=10)
        self.assertContains(self.client.post(other.detail_url, {"action": "extend"}), "до окончания срока")

    def test_week_boundary_combined_filters_and_empty_result(self):
        task = CourseTask.objects.get(week__course__student=self.a, status="started")
        sunday = datetime(2026, 11, 22, 23, 59, tzinfo=NOW.tzinfo)
        self.clock.return_value = sunday
        url = reverse("task_list")
        query = {"status": ["started", "draft"], "course": [task.week.course_id, "invalid"]}
        Notice.objects.filter(pk=task.notice_id).update(due_at=sunday + timedelta(minutes=1))
        self.assertEqual(self.client.get(url, query).context["groups"], {"Далее": [task]})
        self.clock.return_value = sunday + timedelta(minutes=1)
        self.assertEqual(self.client.get(url, query).context["groups"], {"Эта неделя": [task]})
        self.assertContains(self.client.get(url, {"status": "draft"}), "По выбранным фильтрам заданий нет")

    def test_private_pages_actions_and_csrf(self):
        task = CourseTask.objects.filter(week__course__student=self.b).first()
        paths = [task.detail_url, reverse("course_material", args=[task.week_id]),
                 reverse("course_detail", args=[task.week.course_id]), reverse("course_chat", args=[task.week.course_id])]
        for path in paths:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(task.detail_url, {"action": "extend"}).status_code, 404)
        self.assertEqual(self.client.post(paths[-1], {"body": "Чужой чат"}).status_code, 404)
        self.assertContains(self.client.get(reverse("task_list"), {"course": task.week.course_id}), "заданий нет")
        self.client.force_login(self.teacher)
        for path in paths + [reverse("course_catalog"), reverse("task_list")]:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.client.logout()
        for path in paths:
            self.assertRedirects(self.client.get(path), reverse("login") + "?next=" + path)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.b.user)
        self.assertEqual(csrf_client.post(task.detail_url, {"action": "extend"}).status_code, 403)
        self.assertIn("no-store", csrf_client.get(task.detail_url)["Cache-Control"])

    def test_chat_visible_only_within_course_and_group(self):
        course = CourseResult.objects.filter(student=self.a).first()
        url = reverse("course_chat", args=[course.pk])
        self.assertEqual(self.client.post(url, {"body": "<Пример>"}).status_code, 302)
        self.assertContains(self.client.get(url), "&lt;Пример&gt;")
        self.assertEqual(CourseMessage.objects.count(), 1)
        # Вторая персональная запись того же курса сначала относится к другой группе.
        twin = CourseResult.objects.create(student=self.b, title=course.title, assessment_type="Экзамен")
        self.client.force_login(self.b.user)
        url = reverse("course_chat", args=[twin.pk])
        self.assertNotContains(self.client.get(url), "&lt;Пример&gt;")
        StudentProfile.objects.filter(pk=self.b.pk).update(group_name=self.a.group_name)
        self.assertContains(self.client.get(url), "&lt;Пример&gt;")


class ConcurrentExtensionTests(TransactionTestCase):
    def test_two_clicks_cost_one_day(self):
        seed()
        student = StudentProfile.objects.get(user__username="student_a")
        task = CourseTask.objects.get(week__course__student=student, status="started")
        original = task.notice.due_at
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(student.user)
        barrier = Barrier(2)

        def extend(client):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return client.post(task.detail_url, {"action": "extend"}).status_code
            finally:
                close_old_connections()
        with patch("django.utils.timezone.now", return_value=NOW), ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(extend, clients)), [200, 302])
        student.refresh_from_db()
        task.notice.refresh_from_db()
        self.assertEqual((student.late_days, task.notice.due_at), (2, original + timedelta(days=1)))
