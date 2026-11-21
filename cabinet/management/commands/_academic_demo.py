from datetime import date, datetime, time, timedelta

from django.utils import timezone

from cabinet.models import Attendance, CourseResult, Exam, Lesson, Notice


# Фиксированные даты показа сохраняют адреса занятий после повторного seed_demo.
WEEK_START = date(2026, 11, 16)
ALGEBRA = "Линейная алгебра"
LAW = "Гражданское право"


def at(day, hour, minute=0):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def seed_academics(student, employee=None):
    economics = student.group_name == "ЭК-21"
    if economics:
        subject, teacher, room, new_room = ALGEBRA, "Анна Соколова", "304", "218"
        moved_on, weekdays, start = date(2026, 11, 20), (0, 2, 4, 5), time(10, 40)
        seminar = ("Микроэкономика", "Олег Белов", "115")
        grade, credit, pending = 5, "Академическое письмо", "Статистика"
        exam_day, exam_room = date(2026, 12, 2), "310"
        task, due_on = "Сдать задачи по алгебре", moved_on
    else:
        subject, teacher, room, new_room = LAW, "Мария Громова", "107", "312"
        moved_on, weekdays, start = date(2026, 11, 23), (0, 1, 3, 5), time(13, 20)
        seminar = ("Теория государства", "Лев Новиков", "204")
        grade, credit, pending = 4, "Юридическая риторика", "История права"
        exam_day, exam_room = date(2026, 12, 4), "405"
        task, due_on = "Сдать разбор судебного дела", date(2026, 11, 24)

    workshops = [
        ("Статистика", "Анна Соколова", "310"),
        ("Финансовый анализ", "Вера Нестерова", "212"),
        ("Деловая коммуникация", "Михаил Орлов", "106"),
    ] if economics else [
        ("История права", "Ирина Седова", "405"),
        ("Правовая аналитика", "Вадим Елисеев", "210"),
        ("Судебная практика", "Кирилл Власов", "109"),
    ]
    for offset in range(16):  # Две полные недели и начало следующей после 28 ноября.
        day = WEEK_START + timedelta(days=offset)
        if day.weekday() not in weekdays:
            continue
        starts_at = timezone.make_aware(datetime.combine(day, start))
        moved = day == moved_on
        topic, lecturer, normal_room = seminar if day.weekday() == 5 else (subject, teacher, room)
        lesson, _ = Lesson.objects.get_or_create(
            group_name=student.group_name, starts_at=starts_at,
            defaults={"subject": topic, "teacher": lecturer, "ends_at": starts_at + timedelta(minutes=90),
                      "room": new_room if moved else normal_room, "old_room": normal_room if moved else ""},
        )
        daily = [lesson]
        slots = [(12, 30), (14, 20)] if economics else [(15, 10), (16, 50)]
        for index, (hour, minute) in enumerate(slots):
            name, tutor, location = workshops[(offset + index) % len(workshops)]
            begins = at(day, hour, minute)
            workshop, _ = Lesson.objects.get_or_create(group_name=student.group_name, starts_at=begins,
                defaults={"subject": name, "teacher": tutor, "room": location,
                          "ends_at": begins + timedelta(minutes=90)})
            daily.append(workshop)
        for index, entry in enumerate(daily):
            if employee and entry.teacher == employee.full_name and entry.instructor_id is None:
                entry.instructor = employee
                entry.save(update_fields=["instructor"])
            if entry.ends_at <= timezone.now():
                Attendance.objects.get_or_create(student=student, lesson=entry,
                    defaults={"present": (offset + index) % 5 != 2})
        if moved:
            Notice.objects.get_or_create(
                recipient=student, lesson=lesson,
                defaults={"category": Notice.Category.CHANGE, "source": "Учебная часть",
                          "created_at": at(date(2026, 11, 19), 16)},
            )

    for title, assessment, mark, passed in [
        (subject, CourseResult.Assessment.EXAM, grade, None),
        (credit, CourseResult.Assessment.CREDIT, None, True),
        (pending, CourseResult.Assessment.EXAM, None, None),
        (workshops[1][0], CourseResult.Assessment.EXAM, 4, None),
        (workshops[2][0], CourseResult.Assessment.EXAM, 3, None),
    ]:
        course, _ = CourseResult.objects.get_or_create(
            student=student, title=title,
            defaults={"assessment_type": assessment, "grade": mark, "passed": passed},
        )
        if title == pending:
            Exam.objects.get_or_create(course=course, starts_at=at(exam_day, 10), defaults={"room": exam_room})

    published = at(WEEK_START, 9)
    for category, headline, body, due_at in [
        (Notice.Category.ANNOUNCEMENT, "Часы приёма деканата",
         "В будни деканат принимает студентов с 14:00 до 17:00.", None),
        (Notice.Category.DEADLINE, task, "Загрузите работу в учебный кабинет.", at(due_on, 18)),
        (Notice.Category.DEADLINE, f"Подтвердить запись на экзамен «{pending}»",
         "Подтвердите запись у преподавателя.", at(date(2026, 11, 30), 18)),
    ]:
        Notice.objects.get_or_create(
            recipient=student, category=category, headline=headline, created_at=published,
            defaults={"text": body, "source": "Деканат", "due_at": due_at},
        )
