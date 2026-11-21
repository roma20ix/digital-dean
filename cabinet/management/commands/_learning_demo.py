from datetime import date

from cabinet.models import CourseResult, CourseTask, CourseWeek, Notice


def seed_learning(student, subject, pending, credit, workshops, task_title, published, at):
    math = student.group_name == "ЭК-21"
    topics = ("Векторы и линейные комбинации", "Матрица как преобразование") if math else (
        "Условия договора", "Исполнение обязательств")
    materials = (
        "Сложите координаты двух перемещений по отдельности. Путь (2, 1), затем (1, 3) "
        "заканчивается в точке (3, 4). Проверьте результат на координатной сетке.",
        "Диагональная матрица с диагональю (2, 3) удваивает первую координату и утраивает вторую. "
        "Образ вектора (1, 2) равен (2, 6).",
    ) if math else (
        "В учебном договоре мастер обещал сделать полку за десять дней. Разделите описание на стороны, "
        "предмет и срок. Для каждого элемента укажите фразу, из которой он следует.",
        "Мастер передал полку на восьмой день. Заказчик подписал акт. Составьте хронологию и отделите "
        "само действие от документа, который его подтверждает.",
    )
    syllabus = ("Сложение векторов, линейные преобразования и проверка вычислений на простых примерах."
                if math else "Чтение договора, разбор обязательств и составление хронологии исполнения.")
    courses = {course.title: course for course in CourseResult.objects.filter(student=student)}
    for title, category in [(credit, "internal"), (workshops[1][0], "elective"), (workshops[2][0], "audit")]:
        CourseResult.objects.filter(pk=courses[title].pk, category="required").update(category=category)
    main = courses[subject]
    CourseResult.objects.filter(pk=main.pk, syllabus="").update(syllabus=syllabus)
    weeks = []
    for i, (topic, material) in enumerate(zip(topics, materials), 1):
        week, _ = CourseWeek.objects.get_or_create(course=main, number=i, defaults={
            "title": topic, "material": material,
            "recording": ("learning/vectors.webm" if math else "learning/contract.webm") if i == 1 else "",
        })
        weeks.append(week)
    exam_week, _ = CourseWeek.objects.get_or_create(course=courses[pending], number=1, defaults={
        "title": "Подготовка к экзамену",
        "material": "Проверьте время и аудиторию в ведомости. Затем отправьте подтверждение участия.",
    })
    status = CourseTask.Status
    examples = [
        (weeks[0], task_title, None, status.ASSIGNED,
         "Найдите сумму (3, 2) и (−1, 4). Покажите вычисление каждой координаты." if math else
         "Мастер обещал передать полку к пятнице и передал в четверг. Опишите обязательство и факт исполнения."),
        (weeks[0], "Сложение перемещений" if math else "Стороны соглашения", 17, status.GRADED,
         "Приведите собственный пример по материалу первой недели и поясните ответ."),
        (weeks[1], "Проверка преобразования" if math else "Акт приёмки", 26, status.STARTED,
         "Примените метод из материала второй недели к собственному примеру. Запишите исходные данные и результат."),
        (weeks[1], "Сравнение двух решений" if math else "Хронология сделки", 19, status.REVIEW,
         "Предложите два способа проверить вывод по теме недели."),
        (exam_week, f"Подтвердить запись на экзамен «{pending}»", None, status.ASSIGNED,
         "Откройте ведомость, сверьте дату экзамена и подтвердите участие текстовым ответом."),
    ]
    for week, title, day, initial_status, instructions in examples:
        key = {"recipient": student, "headline": title, "category": Notice.Category.DEADLINE, "created_at": published}
        if day is None:
            notice = Notice.objects.get(**key)
        else:
            notice, _ = Notice.objects.get_or_create(**key, defaults={
                "source": "Учебная часть", "text": "Откройте условие в курсе.", "due_at": at(date(2026, 11, day), 18),
            })
        defaults = {"week": week, "instructions": instructions, "status": initial_status}
        if initial_status in (status.GRADED, status.REVIEW):
            defaults.update(answer=week.material, submitted_at=notice.due_at)
        if initial_status == status.GRADED:
            defaults["score"] = 9 if math else 8
        CourseTask.objects.get_or_create(notice=notice, defaults=defaults)
