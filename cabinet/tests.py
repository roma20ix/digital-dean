from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse


class FoundationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("student", password="test-only")

    def test_public_health(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok\n")
        self.assertEqual(response["Content-Type"], "text/plain")

    def test_guest_access(self):
        for path in ("/", "/profile/", "/schedule/", "/study/", "/requests/",
                     "/requests/new/", "/requests/1/", "/inbox/", "/inbox/1/read/", "/logout/"):
            with self.subTest(path=path):
                self.assertRedirects(self.client.get(path), f"/login/?next={path}")

    def test_login_render_and_logout(self):
        self.assertRedirects(self.client.post("/login/", {"username": "student", "password": "test-only"}), "/")
        self.assertTrue(Session.objects.filter(session_key=self.client.session.session_key).exists())
        for route, template in [
            ("today", "today.html"), ("profile", "profile.html"), ("schedule", "schedule.html"),
            ("study", "study.html"), ("requests", "requests/list.html"),
            ("request_new", "requests/new.html"), ("inbox", "inbox.html"),
        ]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/login/")
        self.assertRedirects(self.client.get("/profile/"), "/login/?next=/profile/")

    def test_empty_records_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.get("/requests/1/").status_code, 404)
        self.assertEqual(client.get("/inbox/1/read/").status_code, 405)
        for path in ("/requests/new/", "/inbox/1/read/", "/logout/"):
            self.assertEqual(client.post(path).status_code, 403)
        client.get("/requests/new/")
        csrf = {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}
        self.assertEqual(client.post("/inbox/1/read/", csrf).status_code, 404)
        self.assertIn("submission_token", client.post("/requests/new/", csrf).context["form"].errors)

    def test_empty_week(self):
        self.client.force_login(self.user)
        response = self.client.get("/schedule/", {"mode": "week", "date": "2026-11-19"})
        self.assertEqual(len(response.context["days"]), 7)
        self.assertEqual(response.context["days"][0]["date"].isoformat(), "2026-11-16")
        self.assertIn("date=2026-11-26", response.context["next_url"])
