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


class Lesson(models.Model):
    group_name = models.CharField(max_length=40)
    subject = models.CharField(max_length=200)
    teacher = models.CharField(max_length=200)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    room = models.CharField(max_length=40)
    old_room = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["group_name", "starts_at"], name="group_lesson_slot"),
            models.CheckConstraint(condition=models.Q(ends_at__gt=models.F("starts_at")), name="lesson_positive_time"),
        ]

    @property
    def detail_url(self):
        day = timezone.localdate(self.starts_at)
        return reverse("schedule", query={"mode": "day", "date": day}, fragment=f"lesson-{self.pk}")


class CourseResult(models.Model):
    class Assessment(models.TextChoices):
        EXAM = "Экзамен"
        CREDIT = "Зачёт"

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=16, choices=Assessment.choices)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["title"]
        constraints = [models.UniqueConstraint(fields=["student", "title"], name="student_course")]

    @property
    def credit_label(self):
        if self.assessment_type == self.Assessment.CREDIT:
            return {True: "Зачтено", False: "Не зачтено", None: "Зачёт пока не выставлен"}[self.passed]
        return str(self.grade) if self.grade is not None else "Оценка пока не выставлена"


class Exam(models.Model):
    course = models.ForeignKey(CourseResult, on_delete=models.CASCADE)
    starts_at = models.DateTimeField()
    room = models.CharField(max_length=40)

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [models.UniqueConstraint(fields=["course", "starts_at"], name="course_exam_slot")]

    @property
    def course_title(self):
        return self.course.title


class Notice(models.Model):
    class Category(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Объявление"
        DEADLINE = "deadline", "Срок"
        CHANGE = "change", "Перенос"

    recipient = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    category = models.CharField(max_length=16, choices=Category.choices)
    source = models.CharField(max_length=200)
    headline = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField(null=True, blank=True)
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["recipient", "lesson"], name="student_lesson_notice"),
            models.UniqueConstraint(fields=["recipient", "category", "headline", "created_at"],
                                    condition=models.Q(lesson__isnull=True), name="student_notice_publication"),
            models.CheckConstraint(
                condition=(models.Q(category="change", lesson__isnull=False) |
                           (~models.Q(category="change") & models.Q(lesson__isnull=True))),
                name="change_has_lesson",
            ),
        ]

    @property
    def title(self):
        if self.lesson_id:
            return f"Перенос занятия «{self.lesson.subject}»"
        return self.headline

    @property
    def body(self):
        if self.lesson_id:
            lesson = self.lesson
            when = timezone.localtime(lesson.starts_at)
            return f"{when:%d.%m.%Y в %H:%M}. Прежняя аудитория — {lesson.old_room}, новая — {lesson.room}."
        if self.due_at:
            due = timezone.localtime(self.due_at)
            return f"{self.text} Срок — {due:%d.%m.%Y в %H:%M}."
        return self.text

    @property
    def target_url(self):
        if self.lesson_id:
            return self.lesson.detail_url
        return reverse("inbox")
