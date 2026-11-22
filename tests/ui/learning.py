"""Учебный путь в Chromium на настоящих Django-страницах с собственными демоданными."""
import os
from datetime import datetime
from pathlib import Path
from secrets import token_urlsafe
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from playwright.sync_api import expect, sync_playwright


class LearningJourney(StaticLiveServerTestCase):
    def test_two_students_at_two_sizes(self):
        passwords = {login: token_urlsafe() for login in ("student_a", "student_b")}
        friday = datetime(2026, 11, 20, 9, tzinfo=ZoneInfo("Europe/Moscow"))
        with patch.dict(os.environ, DEMO_STUDENT_A_PASSWORD=passwords["student_a"],
                        DEMO_STUDENT_B_PASSWORD=passwords["student_b"]), patch("django.utils.timezone.now", return_value=friday):
            call_command("seed_demo")
            with sync_playwright() as driver:
                browser = driver.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
                for width, height in [(360, 740), (1280, 800)]:
                    for login, course, title in [
                        ("student_a", "Линейная алгебра", "Сдать задачи по алгебре"),
                        ("student_b", "Гражданское право", "Сдать разбор судебного дела"),
                    ]:
                        with self.subTest(login=login, width=width):
                            page = browser.new_page(viewport={"width": width, "height": height})
                            try:
                                self.journey(page, width, login, passwords[login], course, title)
                            finally:
                                page.close()
                browser.close()

    def journey(self, page, width, login, password, course, title):
        def fits(name):
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), width, name)
            if os.getenv("LEARNING_SCREEN_DIR"):
                page.screenshot(animations="disabled", path=Path(os.environ["LEARNING_SCREEN_DIR"]) / f"{login}-{width}-{name}.png")

        page.goto(self.live_server_url + "/login/")
        page.get_by_label("Имя пользователя").fill(login)
        page.locator("[name=password]").fill(password)
        page.locator("[name=password]").press("Enter")
        deadline = page.get_by_role("link", name=title, exact=True)
        target = deadline.get_attribute("href")
        deadline.click()
        expect(page.get_by_role("heading", name=title)).to_be_visible()
        fits("task")
        page.get_by_role("link", name="← " + course).click()
        expect(page.get_by_role("heading", name=course, exact=True)).to_be_visible()
        expect(page.get_by_role("complementary", name="Сведения о курсе").get_by_role("link", name=title)).to_have_attribute("href", target)
        slider = page.locator("#goal-target")
        slider.focus()
        slider.press("End")
        expect(page.locator(".goal-answer")).to_contain_text("этой цели пока не достичь")
        slider.press("Home")
        expect(page.locator(".goal-answer")).to_contain_text("уже достигнута")
        self.assertEqual(page.locator(".goal-chart-target").count(), 1)
        page.locator(".unit summary").first.press("Enter")
        expect(page.locator(".week-links").get_by_role("link", name=title)).to_have_attribute("href", target)
        fits("course")
        page.get_by_role("link", name="Материалы недели 1").click()
        expect(page.locator("article")).to_be_visible()
        page.get_by_role("link", name="← " + course).click()
        page.get_by_role("link", name="Видеозаписи").click()
        page.locator("video").evaluate("(v) => v.play()")
        self.assertGreater(page.locator("video").evaluate("(v) => v.duration"), 0)
        page.get_by_role("link", name="Все курсы").click()
        fits("catalog")
        page.goto(self.live_server_url + "/study/")
        page.locator(".result").first.hover()
        self.assertEqual(page.locator(".result").first.evaluate("el => getComputedStyle(el).backgroundColor"), "rgba(0, 0, 0, 0)")
        page.goto(self.live_server_url + "/study/courses/")
        page.get_by_role("link", name="Факультативные", exact=True).click()
        expect(page.locator(".course-card")).to_have_count(1)
        page.get_by_role("link", name="Мои задания", exact=True).click()
        page.get_by_text("Курсы", exact=True).click()
        page.get_by_label(course, exact=True).check()
        page.get_by_text("Статусы", exact=True).click()
        page.get_by_label("Задано", exact=True).check()
        page.get_by_role("button", name="Применить").click()
        expect(page.locator(".task-row")).to_have_count(1)
        expect(page.get_by_role("link", name=title)).to_have_attribute("href", target)
        fits("tasks")
        page.goto(self.live_server_url + "/inbox/")
        page.get_by_role("link", name=title, exact=True).click()
        self.assertEqual(page.url, self.live_server_url + target)
        if width == 1280:
            page.get_by_role("button", name="Перенести на один день").click()
            expect(page.get_by_text("Срок перенесён на один день.")).to_be_visible()
            page.get_by_label("Ваше решение").fill("Ответ демостудента")
            page.get_by_role("button", name="Сохранить черновик").click()
            expect(page.get_by_text("Решение прикреплено", exact=True)).to_be_visible()
            review_status = page.get_by_text("На проверке", exact=True)
            page.get_by_role("button", name="Отправить на проверку").click()
            expect(review_status).to_be_visible()
            page.reload()
            expect(review_status).to_be_visible()
            expect(page.get_by_text("Ответ демостудента")).to_be_visible()
