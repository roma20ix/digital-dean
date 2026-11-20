import os
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from secrets import token_urlsafe
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import connections
from django.db.models import QuerySet
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .models import StudentProfile, StudentRequest


def seed_demo(password_a, password_b):
    with patch.dict(os.environ, {
        "DEMO_STUDENT_A_PASSWORD": password_a, "DEMO_STUDENT_B_PASSWORD": password_b,
    }):
        call_command("seed_demo", stdout=StringIO())


def form_token(client):
    form = client.get(reverse("request_new")).context["form"]
    return form["submission_token"].value()


class StudentRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password_a, cls.password_b = token_urlsafe(), token_urlsafe()
        seed_demo(cls.password_a, cls.password_b)

    def login(self, username, password):
        response = self.client.post(reverse("login"), {"username": username, "password": password})
        self.assertRedirects(response, reverse("today"))

    def test_certificate_survives_logout_and_is_private(self):
        self.login("student_a", self.password_a)
        profile_a = self.client.get(reverse("profile")).context["student"]
        original_a = self.client.get(reverse("requests")).context["items"].get()
        self.assertEqual(original_a.status_label, "Готова к выдаче")
        self.assertEqual(len(original_a.history), 2)

        payload = {"kind": "certificate", "submission_token": form_token(self.client)}
        response = self.client.post(reverse("request_new"), payload)
        self.assertEqual(response.status_code, 302)
        url = response.url
        detail = self.client.get(url)
        item = detail.context["item"]
        self.assertEqual(detail.context["history"], [{"at": item.created_at, "label": "Принята"}])
        self.assertEqual(item.kind_label, "Справка об обучении")
        self.assertEqual(item.status_label, "Принята")
        self.assertRedirects(self.client.post(reverse("request_new"), payload), url)
        self.assertEqual(self.client.get(reverse("today")).context["latest_request"], item)
        self.assertEqual(list(self.client.get(reverse("requests")).context["items"]), [item, original_a])

        self.client.post(reverse("logout"))
        self.assertRedirects(self.client.get(url), reverse("login") + "?next=" + url)
        self.login("student_b", self.password_b)
        profile_b = self.client.get(reverse("profile"), {"student_id": profile_a.user_id}).context["student"]
        for field in ("full_name", "faculty", "program", "year", "group_name"):
            self.assertNotEqual(getattr(profile_a, field), getattr(profile_b, field))
        original_b = self.client.get(reverse("requests")).context["items"].get()
        self.assertEqual(original_b.kind, "appeal")
        self.assertEqual(self.client.get(reverse("today")).context["latest_request"], original_b)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(original_a.detail_url).status_code, 404)
        self.assertIn("submission_token", self.client.post(reverse("request_new"), payload).context["form"].errors)

        self.client.post(reverse("logout"))
        self.login("student_a", self.password_a)
        self.assertEqual(self.client.get(original_b.detail_url).status_code, 404)
        self.assertEqual(self.client.get(url).context["item"].pk, item.pk)
        self.assertEqual(self.client.get(url).context["item"].status_label, "Принята")

    def test_validation_and_appeal(self):
        self.login("student_b", self.password_b)
        token = form_token(self.client)
        url = reverse("request_new")
        data = {"submission_token": token, "kind": "appeal", "message": "  "}
        self.assertFormError(self.client.post(url, data).context["form"], "message",
                             "Введите текст обращения в деканат.")
        data.update(kind="unknown", message="Уточните срок выдачи.")
        form = self.client.post(url, data).context["form"]
        self.assertIn("kind", form.errors)
        self.assertEqual(form["message"].value(), data["message"])
        self.assertEqual(form["submission_token"].value(), token)
        self.assertEqual(StudentRequest.objects.count(), 2)
        data.update(kind="appeal", owner=999, ready_at="2020-01-01", status="ready")
        reply = self.client.post(url, data)
        item = self.client.get(reply.url).context["item"]
        self.assertEqual(item.message, data["message"])
        self.assertEqual(item.owner.username, "student_b")
        self.assertEqual(item.status_label, "Принята")
        self.assertEqual(item.kind_label, "Обращение в деканат")

    def test_reseed_preserves_students_history_and_new_requests(self):
        self.login("student_a", self.password_a)
        reply = self.client.post(reverse("request_new"), {"kind": "certificate",
                                                          "submission_token": form_token(self.client)})
        before = list(StudentRequest.objects.values())
        seed_demo(self.password_a, self.password_b)
        self.assertEqual(list(StudentRequest.objects.values()), before)
        self.assertEqual(get_user_model().objects.count(), 2)
        self.assertEqual(StudentProfile.objects.count(), 2)
        self.assertFalse(get_user_model().objects.filter(is_staff=True).exists())
        self.assertFalse(get_user_model().objects.filter(is_superuser=True).exists())
        self.assertEqual(self.client.get(reply.url).status_code, 200)
        self.assertFalse(self.client.login(username="student_b", password=self.password_a))

    def test_seed_rejects_missing_or_shared_password(self):
        for password in ("", self.password_a):
            with self.assertRaises(CommandError):
                seed_demo(self.password_a, password)


class ConcurrentSubmissionTests(TransactionTestCase):
    def test_simultaneous_posts_redirect_to_one_request(self):
        user = get_user_model().objects.create_user("concurrent")
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(user)
        payload = {"kind": "certificate", "submission_token": form_token(clients[0])}
        ready_to_insert = Barrier(2)
        original_create = QuerySet.create

        def simultaneous_create(queryset, **kwargs):
            # Оба запроса должны пройти поиск до того, как первый выполнит INSERT.
            if queryset.model is StudentRequest:
                ready_to_insert.wait(timeout=10)
            return original_create(queryset, **kwargs)

        def submit(client):
            try:
                response = client.post(reverse("request_new"), payload)
                return response.status_code, response.headers.get("Location")
            finally:
                connections.close_all()

        with patch.object(QuerySet, "create", simultaneous_create):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, clients))
        only_request = StudentRequest.objects.get(owner=user)
        self.assertEqual(results, [(302, only_request.detail_url)] * 2)
