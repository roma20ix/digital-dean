import os
from collections import Counter
from io import BytesIO, StringIO
from secrets import token_urlsafe
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from .models import Lesson


class EmployeeAndAppearanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = token_urlsafe()
        secrets = dict(DEMO_TEACHER_PASSWORD=cls.password,
                       DEMO_STUDENT_A_PASSWORD=token_urlsafe(), DEMO_STUDENT_B_PASSWORD=token_urlsafe())
        with patch.dict(os.environ, secrets):
            call_command("seed_demo", stdout=StringIO())
            call_command("seed_demo", stdout=StringIO())
        cls.student = get_user_model().objects.get(username="student_a")

    def test_employee_schedule_and_role(self):
        self.assertTrue(self.client.login(username="teacher_a", password=self.password))
        self.assertContains(self.client.get("/"), "Кабинет преподавателя")
        self.assertContains(self.client.get("/profile/"), "Кафедра прикладной математики")
        response = self.client.get("/schedule/?mode=week&date=2026-11-20")
        lessons = [lesson for day in response.context["days"] for lesson in day["lessons"]]
        self.assertTrue(lessons)
        self.assertTrue(all(lesson.instructor.user.username == "teacher_a" for lesson in lessons))
        self.assertEqual(self.client.post("/requests/new/").status_code, 404)
        self.assertEqual(self.client.get("/attendance/").status_code, 404)
        for group in ("ЭК-21", "ЮР-11"):
            starts = Lesson.objects.filter(group_name=group).values_list("starts_at", flat=True)
            counts = Counter(timezone.localdate(start) for start in starts)
            self.assertEqual(set(counts.values()), {3})

    def test_avatar_and_preferences_belong_to_session_owner(self):
        self.client.force_login(self.student)
        self.assertFalse(self.client.get("/profile/").context["appearance_form"].is_bound)
        data = BytesIO()
        Image.new("RGB", (400, 600), "teal").save(data, format="PNG")
        image = SimpleUploadedFile("test.png", data.getvalue(), "image/png")
        self.assertRedirects(self.client.post("/profile/", {"accent": "forest", "photo": image}), "/profile/?saved=1")
        self.assertContains(self.client.get("/profile/?saved=1"), "Настройки сохранены.")
        self.client.logout()
        self.client.force_login(self.student)
        response = self.client.get("/profile/avatar/")
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(Image.open(BytesIO(response.content)).size, (256, 256))
        invalid = SimpleUploadedFile("broken.png", b"invalid", "image/png")
        self.assertContains(self.client.post("/profile/", {"photo": invalid, "accent": "amber"}), "исправное изображение")
        self.assertContains(self.client.get("/"), 'data-accent="forest"')
        self.client.force_login(get_user_model().objects.get(username="student_b"))
        self.assertEqual(self.client.get("/profile/avatar/", {"user": self.student.pk}).status_code, 404)
        self.client.force_login(self.student)
        self.client.post("/profile/", {"accent": "ocean", "remove": "on"})
        self.assertEqual(self.client.get("/profile/avatar/").status_code, 404)
