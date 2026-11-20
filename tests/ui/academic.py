"""UI contract scenarios; run with manage.py test tests.ui.academic."""
import os
from datetime import datetime
from secrets import token_urlsafe
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.shortcuts import render
from django.urls import reverse
from playwright.sync_api import expect, sync_playwright


class AcademicJourney(StaticLiveServerTestCase):
    def test_calendar_study_and_inbox(self):
        password = token_urlsafe()
        get_user_model().objects.create_user("academic-test", password=password)
        with sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
            page = browser.new_page(viewport={"width": 360, "height": 740})
            page.goto(self.live_server_url + reverse("login"))
            page.locator('[name=username]').fill("academic-test")
            page.locator('[name=password]').fill("wrong")
            page.locator('[name=password]').press("Enter")
            expect(page.locator(".errorlist")).to_be_visible()
            page.locator('[name=password]').fill(password)
            page.locator('[name=password]').press("Enter")
            expect(page.get_by_role("heading", name="Сегодня")).to_be_visible()
            page.goto(self.live_server_url + "/schedule/?mode=day&date=2026-11-22")
            expect(page.get_by_text("Занятий нет.")).to_be_visible()

            # A1 provides calendar navigation. Supply only the missing A2 data in this test.
            with patch("cabinet.views.render", side_effect=self.with_academic_context):
                for width, height in [(360, 740), (1280, 800)]:
                    with self.subTest(width=width):
                        page.set_viewport_size({"width": width, "height": height})
                        self.check_pages(page, width)
            browser.close()

    @staticmethod
    def with_academic_context(request, template, context, **kwargs):
        starts = datetime(2026, 11, 23, 10, 40, tzinfo=ZoneInfo("Europe/Moscow"))
        target = "/schedule/?mode=day&date=2026-11-23#lesson-17"
        subject = "Математические методы моделирования распределённых информационных систем"
        lesson = dict(id=17, subject=subject, starts_at=starts, ends_at=starts.replace(hour=12, minute=10),
                      teacher="Анна Соколова", old_room="304", room="218", detail_url=target)
        notice = dict(id=7, category="change", title="Занятие перенесено", source="Деканат",
                      body="Прежняя аудитория — 304. Новая аудитория — 218.",
                      created_at=starts, is_read=False, target_url=target)
        if template == "inbox.html":
            context["items"] = [notice]
        elif template == "schedule.html":
            for day in context["days"]:
                day["lessons"] = [lesson] if day["date"] == starts.date() else []
            if context["date"] == "2026-11-22":
                context["next_teaching_url"] = target
        elif template == "today.html":
            context.update(next_lesson=None, changes=[notice],
                           next_deadline=dict(title="Сдать задачи", due_at=starts, target_url="/study/"))
        elif template == "study.html":
            context["courses"] = [
                dict(title=subject, grade=2, credit_label=""),
                dict(title="Физика", grade=None, credit_label=""),
                dict(title="История", grade=None, assessment_type="Зачёт", credit_label="Зачтено"),
            ]
            context["exams"] = [dict(course_title=subject, starts_at=starts, room="218")]
        return render(request, template, context, **kwargs)

    def check_pages(self, page, width):
        def fits():
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), width)

        def follow(label):
            link = page.get_by_role("link", name=label, exact=True)
            for _ in range(35):
                page.keyboard.press("Tab")
                if link.evaluate("el => el === document.activeElement"):
                    break
            expect(link).to_be_focused()
            self.assertEqual(link.evaluate("el => getComputedStyle(el).outlineStyle"), "solid")
            with page.expect_navigation():
                page.keyboard.press("Enter")

        page.goto(self.live_server_url + "/")
        expect(page.get_by_text("На сегодня больше пар нет.")).to_be_visible()
        expect(page.get_by_text("Сдать задачи")).to_be_visible()
        fits()
        follow("Открыть расписание")
        page.goto(self.live_server_url + reverse("inbox"))
        fits()
        follow("Занятие перенесено")
        self.assertTrue(page.url.endswith("date=2026-11-23#lesson-17"))
        card = page.locator(":target")
        expect(card).to_be_in_viewport(ratio=1)
        expect(card).to_contain_text("Прежняя аудитория — 304")
        expect(card).to_contain_text("Новая аудитория — 218")
        fits()
        follow("Неделя")
        expect(page.get_by_role("link", name="День", exact=True)).to_have_attribute("href", "?mode=day&date=2026-11-23")
        self.assertEqual(page.locator(".day").count(), 7)
        expect(page.get_by_text("Занятий нет.").first).to_be_visible()
        fits()
        page.goto(self.live_server_url + reverse("study"))
        for result in ("Неудовлетворительно", "Оценки пока нет", "Зачтено", "Сессия"):
            expect(page.get_by_text(result, exact=False)).to_be_visible()
        fits()
