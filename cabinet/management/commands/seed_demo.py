import os
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cabinet.models import StudentProfile, StudentRequest


class Command(BaseCommand):
    help = "Создать двух демостудентов и примеры заявок."

    @transaction.atomic
    def handle(self, *args, **options):
        password_a = os.environ.get("DEMO_STUDENT_A_PASSWORD", "")
        password_b = os.environ.get("DEMO_STUDENT_B_PASSWORD", "")
        if not password_a.strip() or not password_b.strip() or password_a == password_b:
            raise CommandError("Задайте разные DEMO_STUDENT_A_PASSWORD и DEMO_STUDENT_B_PASSWORD.")

        profiles = [
            ("student_a", password_a, "Алина Соколова", "Экономический", "Экономика", 2, "ЭК-21"),
            ("student_b", password_b, "Илья Волков", "Правовой", "Юриспруденция", 1, "ЮР-11"),
        ]
        for username, password, full_name, faculty, program, year, group in profiles:
            user, created = get_user_model().objects.get_or_create(username=username)
            if not created and (user.is_staff or user.is_superuser or
                                not StudentProfile.objects.filter(user=user, is_demo=True).exists()):
                raise CommandError(f"Логин {username} уже занят другой учётной записью.")
            if not user.check_password(password):
                user.set_password(password)
                user.save(update_fields=["password"])
            StudentProfile.objects.update_or_create(user=user, defaults={
                "is_demo": True, "full_name": full_name, "faculty": faculty,
                "program": program, "year": year, "group_name": group,
            })
            created_at = timezone.now() - timedelta(days=3)
            if username == "student_a":
                example = {"kind": StudentRequest.Kind.CERTIFICATE,
                           "message": "Демоданные: ранее заказанная справка.",
                           "ready_at": created_at + timedelta(days=1)}
            else:
                example = {"kind": StudentRequest.Kind.APPEAL,
                           "message": "Демоданные: когда можно забрать документы?"}
            StudentRequest.objects.get_or_create(
                owner=user, submission_token=uuid5(NAMESPACE_URL, f"digital-dean/demo/{username}"),
                defaults={**example, "created_at": created_at},
            )
        self.stdout.write("Подготовлены демоаккаунты student_a и student_b.")
