"""Integration with the A2 demo database; no replacement view contexts."""
import os
from datetime import datetime
from pathlib import Path
from secrets import token_urlsafe
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from playwright.sync_api import expect, sync_playwright


class AcademicDemo(StaticLiveServerTestCase):
    def test_demo_journey(self):
        password = token_urlsafe()
        with patch.dict(os.environ, DEMO_STUDENT_A_PASSWORD=password, DEMO_STUDENT_B_PASSWORD=token_urlsafe()):
            call_command("seed_demo")
        sunday = datetime(2026, 11, 22, 9, tzinfo=ZoneInfo("Europe/Moscow"))
        # Align Django's now template tag and the server's academic date for the Sunday scenario.
        with patch("django.utils.timezone.now", return_value=sunday), patch("django.template.defaulttags.datetime") as clock:
            clock.now.return_value = sunday
            with sync_playwright() as driver:
                browser = driver.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
                for width, height in [(360, 740), (1280, 800)]:
                    page = browser.new_page(viewport={"width": width, "height": height})
                    page.goto(self.live_server_url + "/login/")
                    page.locator('[name=username]').fill("student_a")
                    page.locator('[name=password]').fill(password)
                    page.locator('[name=password]').press("Enter")
                    expect(page.get_by_role("heading", name="Сегодня")).to_be_visible()

                    def capture(name):
                        self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                        output = os.getenv("B2_SCREEN_DIR")
                        if output:
                            page.screenshot(path=Path(output) / f"{name}-{width}.png", full_page=True)

                    expect(page.get_by_text("На сегодня больше пар нет.")).to_be_visible()
                    expect(page.get_by_text("23 ноября, 10:40", exact=False)).to_be_visible()
                    homework = page.locator("section.card").filter(
                        has=page.get_by_role("heading", name="Ближайшее домашнее задание"))
                    expect(homework.get_by_role("link", name="Проверка преобразования")).to_be_visible()
                    expect(homework.get_by_text("Линейная алгебра", exact=True)).to_be_visible()
                    expect(homework.get_by_text("Сдать до 26 ноября, 18:00 МСК")).to_be_visible()
                    capture("today-empty")
                    page.goto(self.live_server_url + "/schedule/?mode=day&date=2026-11-22")
                    expect(page.get_by_text("Занятий нет.")).to_be_visible()
                    page.get_by_role("link", name="Ближайший учебный день с занятиями").press("Enter")
                    expect(page.locator(":target")).to_be_in_viewport()
                    self.assertIn("date=2026-11-23#", page.url)
                    page.goto(self.live_server_url + "/inbox/")
                    change = page.get_by_role("link", name="Перенос занятия «Линейная алгебра»")
                    capture("inbox")
                    change.press("Enter")
                    expect(page.locator(":target")).to_be_in_viewport(ratio=1)
                    expect(page.locator(":target")).to_contain_text("Новая аудитория — 218")
                    expect(page.locator(":target")).to_contain_text("Прежняя аудитория — 304")
                    self.assertIn("date=2026-11-20#", page.url)
                    capture("day")
                    page.get_by_role("link", name="Неделя", exact=True).press("Enter")
                    expect(page.locator(".day")).to_have_count(7)
                    capture("week")
                    page.goto(self.live_server_url + "/study/")
                    for text in ("Оценки пока нет", "Зачтено", "5", "Сессия", "2 декабря 2026, 10:00"):
                        expect(page.get_by_text(text, exact=(text == "5"))).to_be_visible()
                    capture("study")
                    if width == 1280:
                        page.goto(self.live_server_url + "/inbox/")
                        article = page.get_by_role("article").filter(has=change)
                        article.get_by_role("button").press("Enter")
                        expect(article).to_contain_text("Прочитано")
                        page.reload()
                        expect(article).to_contain_text("Прочитано")
                    page.close()
                browser.close()
