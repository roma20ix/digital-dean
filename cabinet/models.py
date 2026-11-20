from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    faculty = models.CharField(max_length=200)
    program = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField()
    group_name = models.CharField(max_length=40)
    is_demo = models.BooleanField(default=False)


class StudentRequest(models.Model):
    class Kind(models.TextChoices):
        CERTIFICATE = "certificate", "Справка об обучении"
        APPEAL = "appeal", "Обращение в деканат"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submission_token = models.UUIDField()
    kind = models.CharField(max_length=16, choices=Kind.choices)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    ready_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [models.UniqueConstraint(
            fields=["owner", "submission_token"], name="unique_student_submission",
        )]

    @property
    def detail_url(self):
        return reverse("request_detail", kwargs={"pk": self.pk})

    @property
    def kind_label(self):
        return self.get_kind_display()

    @property
    def status_label(self):
        return "Готова к выдаче" if self.ready_at else "Принята"

    @property
    def history(self):
        events = [{"label": "Принята", "at": self.created_at}]
        if self.ready_at:
            events.append({"label": "Готова к выдаче", "at": self.ready_at})
        return events
