from datetime import date, datetime, timedelta, timezone as dt_timezone
from io import StringIO
import os
from secrets import token_urlsafe
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CourseResult, Exam, Lesson, Notice, StudentProfile


class AcademicSectionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.passwords = {key: token_urlsafe() for key in ("DEMO_STUDENT_A_PASSWORD", "DEMO_STUDENT_B_PASSWORD")}
        with patch.dict(os.environ, cls.passwords):
            call_command("seed_demo", stdout=StringIO())
        cls.a = StudentProfile.objects.get(user__username="student_a")
        cls.b = StudentProfile.objects.get(user__username="student_b")

    def setUp(self):
        # 09:00 пятницы в Москве. Остальные тесты не зависят от даты запуска CI.
        self.clock = self.enterContext(patch("django.utils.timezone.now",
                                            return_value=datetime(2026, 11, 20, 6, tzinfo=dt_timezone.utc)))
        self.client.force_login(self.a.user)

    def test_one_transfer_in_dashboard_inbox_and_schedule(self):
        home = self.client.get("/").context
        lesson = home["next_lesson"]
        self.assertEqual((lesson.subject, lesson.teacher, lesson.old_room, lesson.room),
                         ("Линейная алгебра", "Анна Соколова", "304", "218"))
        self.assertEqual(timezone.localtime(lesson.starts_at).strftime("%H:%M"), "10:40")
        change = home["changes"].get()
        self.assertEqual(change.pk, self.client.get("/inbox/").context["items"].get(category="change").pk)
        self.assertEqual(change.target_url, lesson.detail_url)
        path, fragment = change.target_url.split("#")
        selected = self.client.get(path).context
        self.assertEqual(selected["date"], "2026-11-20")
        self.assertEqual(selected["days"][0]["lessons"][0], lesson)
        self.assertEqual(len(selected["days"][0]["lessons"]), 3)
        self.assertEqual(fragment, f"lesson-{lesson.pk}")
        lesson.room = "222"
        lesson.save(update_fields=["room"])
        for notice in (self.client.get("/").context["changes"].get(),
                       self.client.get("/inbox/").context["items"].get(category="change")):
            self.assertIn("222", notice.body)
            self.assertIn("304", notice.body)
            self.assertNotIn("218", notice.body)

    def test_moscow_day_week_and_empty_day(self):
        # В UTC ещё воскресенье. По Москве уже понедельник новой недели.
        self.clock.return_value = datetime(2026, 11, 22, 21, 5, tzinfo=dt_timezone.utc)
        self.client.force_login(self.b.user)
        context = self.client.get("/schedule/", {"mode": "week"}).context
        self.assertEqual(context["date"], "2026-11-23")
        days = context["days"]
        self.assertEqual([day["date"] for day in days], [date(2026, 11, 23) + timedelta(days=i) for i in range(7)])
        self.assertEqual(days[-1]["lessons"], [])
        self.assertEqual(self.client.get(context["prev_url"]).context["date"], "2026-11-16")
        self.assertEqual(self.client.get(context["next_url"]).context["date"], "2026-11-30")
        moved = self.client.get("/").context["next_lesson"]
        self.assertEqual(days[0]["lessons"][0], moved)
        self.assertEqual(len(days[0]["lessons"]), 3)
        self.assertEqual((moved.subject, moved.old_room, moved.room), ("Гражданское право", "107", "312"))
        # Даже если в query есть чужая группа, субботнее занятие относится к ЮР-11.
        empty = self.client.get("/schedule/", {"date": "2026-11-20", "group_name": self.a.group_name}).context
        self.assertEqual(empty["days"][0]["lessons"], [])
        following = self.client.get(empty["next_teaching_url"]).context
        self.assertEqual(following["date"], "2026-11-21")
        self.assertEqual(following["days"][0]["lessons"][0].group_name, self.b.group_name)

    def test_moscow_midnight_includes_only_correct_week(self):
        local_midnight = timezone.make_aware(datetime(2026, 11, 23))
        for offset in (-30, 0):
            starts = local_midnight + timedelta(minutes=offset)
            Lesson.objects.create(group_name=self.a.group_name, subject="Консультация", teacher="И. Левина",
                                  starts_at=starts, ends_at=starts + timedelta(minutes=20), room="210")
        sunday = self.client.get("/schedule/", {"mode": "week", "date": "2026-11-22"}).context["days"][-1]
        monday = self.client.get("/schedule/", {"mode": "week", "date": "2026-11-23"}).context["days"][0]
        self.assertEqual([row.starts_at for row in sunday["lessons"]], [local_midnight - timedelta(minutes=30)])
        self.assertEqual(monday["lessons"][0].starts_at, local_midnight)

    def test_individual_results_upcoming_exams_deadlines_and_next_lesson(self):
        for student, subject, mark, pending, deadline in [
            (self.a, "Линейная алгебра", 5, "Статистика", "Сдать задачи по алгебре"),
            (self.b, "Гражданское право", 4, "История права", "Сдать разбор судебного дела"),
        ]:
            self.client.force_login(student.user)
            study = self.client.get("/study/", {"student_id": self.a.pk}).context
            courses = study["courses"]
            self.assertEqual(set(courses.values_list("student_id", flat=True)), {student.pk})
            self.assertEqual(courses.get(title=subject).grade, mark)
            self.assertEqual(courses.get(assessment_type="Зачёт").credit_label, "Зачтено")
            self.assertIsNone(courses.get(title=pending).grade)
            self.assertEqual(courses.get(title=pending).credit_label, "Оценка пока не выставлена")
            self.assertEqual(study["exams"].get().course_title, pending)
            home = self.client.get("/").context
            self.assertEqual(home["next_deadline"].title, deadline)
            self.assertEqual(home["next_lesson"].group_name, student.group_name)
            self.assertEqual(home["next_deadline"].target_url, home["next_deadline"].work.detail_url)
            self.assertIn("18:00", home["next_deadline"].body)
        self.assertEqual(timezone.localdate(home["next_lesson"].starts_at), date(2026, 11, 21))
        self.clock.return_value = datetime(2026, 12, 5, tzinfo=dt_timezone.utc)
        self.client.force_login(self.b.user)
        self.assertFalse(self.client.get("/study/").context["exams"].exists())
        self.assertIsNone(self.client.get("/").context["next_deadline"])
        self.assertIsNone(self.client.get("/").context["next_lesson"])

    def test_read_is_personal_and_survives_reseed(self):
        items = self.client.get("/inbox/").context["items"]
        timestamps = [notice.created_at for notice in items]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        a_news = items.get(category="announcement")
        b_news = Notice.objects.get(recipient=self.b, category="announcement")
        self.assertEqual(a_news.title, b_news.title)
        self.assertEqual(self.client.post(reverse("notice_read", args=[b_news.pk])).status_code, 404)
        for _ in range(2):
            self.assertRedirects(self.client.post(reverse("notice_read", args=[a_news.pk])), "/inbox/")
        models = (Lesson, CourseResult, Exam, Notice)
        before = [list(model.objects.order_by("pk").values_list("pk", flat=True)) for model in models]
        with patch.dict(os.environ, self.passwords):
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(before, [list(model.objects.order_by("pk").values_list("pk", flat=True)) for model in models])
        a_news.refresh_from_db()
        b_news.refresh_from_db()
        self.assertTrue(a_news.is_read)
        self.assertFalse(b_news.is_read)

    def test_group_change_hides_previous_group_notice(self):
        previous = self.client.get("/").context["changes"].get()
        StudentProfile.objects.filter(pk=self.a.pk).update(group_name=self.b.group_name)
        self.assertFalse(self.client.get("/").context["changes"].exists())
        self.assertNotIn(previous, self.client.get("/inbox/").context["items"])
        self.assertEqual(self.client.post(reverse("notice_read", args=[previous.pk])).status_code, 404)

    def test_panel_marks_only_visible_user_notices(self):
        url = reverse("notice_panel")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertContains(self.client.post(url), "Линейная алгебра")
        self.assertFalse(self.client.get("/").context["has_unread"])
        self.client.force_login(self.b.user)
        self.assertTrue(self.client.get("/").context["has_unread"])

    def test_attendance_uses_own_marks_and_excludes_unmarked(self):
        from .models import Attendance
        past, missed = Lesson.objects.filter(group_name=self.a.group_name, ends_at__lt=timezone.now())[:2]
        Attendance.objects.filter(student=self.a).delete()
        Attendance.objects.update_or_create(student=self.b, lesson=past, defaults={"present": False})
        response = self.client.get(reverse("attendance"))
        courses = response.context["courses"]
        self.assertTrue(courses)
        self.assertTrue(all(course["marked"] == 0 for course in courses))
        self.assertNotContains(response, "attendance-ring")
        Attendance.objects.create(student=self.a, lesson=past, present=True)
        Attendance.objects.create(student=self.a, lesson=missed, present=False)
        response = self.client.get(reverse("attendance"))
        self.assertContains(response, "50%")
        totals = response.context["totals"]
        self.assertEqual((totals["present"], totals["absent"], totals["percent"]), (1, 1, 50))
        self.assertGreater(totals["unmarked"], 0)
        self.assertNotContains(response, "Гражданское право")
