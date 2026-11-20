"""Browser acceptance check. Run explicitly with manage.py test tests.ui.mobile."""
import os
from datetime import timedelta
from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from playwright.sync_api import expect, sync_playwright

from cabinet.models import StudentProfile


class MobileRequestsTest(StaticLiveServerTestCase):
    def test_student_journey(self):
        password = token_urlsafe()
        user = get_user_model().objects.create_user("ui-student", password=password)
        name = "Александра " + "ДлиннаяФамилия" * 10 + " Александровна"
        StudentProfile.objects.create(user=user, full_name=name, faculty="Факультет наук",
                                      program="Математика", year=2, group_name="М-2")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
            page = browser.new_page(viewport={"width": 360, "height": 740})
            page.goto(self.live_server_url + reverse("profile"))
            username = page.locator('[name="username"]')
            secret = page.locator('[name="password"]')

            def fits():
                self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), 360)

            def activate(control):
                for _ in range(30):
                    if control.evaluate("el => el === document.activeElement"):
                        break
                    page.keyboard.press("Tab")
                expect(control).to_be_focused()
                self.assertEqual(control.evaluate("el => getComputedStyle(el).outlineStyle"), "solid")
                if control.evaluate("el => el.tagName === 'SUMMARY'"):
                    page.keyboard.press("Enter")
                else:
                    with page.expect_navigation(wait_until="load"):
                        page.keyboard.press("Enter")

            def section(label):
                activate(page.locator("summary"))
                activate(page.get_by_role("navigation").get_by_text(label, exact=True))

            fits()
            username.fill(user.username)
            secret.fill("wrong")
            activate(page.get_by_role("button", name="Войти"))
            expect(page.locator(".errorlist")).to_be_visible()
            expect(username).to_have_value(user.username)
            secret.fill(password)
            activate(page.get_by_role("button", name="Войти"))
            expect(page.get_by_role("heading", name=name)).to_be_visible()
            fits()

            section("Мои заявки")
            expect(page.get_by_text("Заявок пока нет.")).to_be_visible()
            fits()
            section("Сегодня")
            fits()
            order = page.get_by_role("link", name="Заказать справку")
            activate(order)
            expect(page.get_by_label("Тип заявки")).to_have_value("certificate")
            fits()
            send = page.get_by_role("button", name="Отправить заявку")
            activate(send)
            receipt = page.url
            expect(page.get_by_role("heading", name="Принята")).to_be_visible()
            expect(page.get_by_role("heading", name="Заявка № " + receipt.split("/")[-2])).to_be_visible()
            fits()
            section("Сегодня")
            activate(page.locator(f'main a[href="{receipt.removeprefix(self.live_server_url)}"]'))
            expect(page).to_have_url(receipt)
            activate(page.get_by_role("link", name="← Мои заявки"))
            expect(page.get_by_text("Справка об обучении", exact=False)).to_be_visible()
            activate(page.get_by_role("link", name="Новая заявка"))
            kind = page.get_by_label("Тип заявки")
            kind.select_option("appeal")
            activate(send)
            expect(page.get_by_text("Введите текст обращения в деканат.")).to_be_visible()
            expect(kind).to_have_value("appeal")
            message = page.get_by_label("Текст обращения")
            draft = "Где получить выписку об успеваемости?"
            message.fill(draft)
            # A stale token triggers a server error with a nonempty bound textarea.
            page.locator('[name="submission_token"]').evaluate("el => el.value = 'invalid'")
            activate(send)
            expect(page.get_by_text("Форма недействительна.", exact=False)).to_be_visible()
            expect(message).to_have_value(draft)
            fits()
            activate(page.get_by_role("link", name="Открыть новую форму"))
            kind.select_option("appeal")
            message.fill(draft)
            activate(send)
            expect(page.get_by_text(draft)).to_be_visible()
            browser.close()

    def test_today_with_schedule_context(self):
        starts = timezone.now()
        lesson_url = reverse("schedule") + "?mode=day#lesson-17"
        html = render_to_string("today.html", {
            "student": {"full_name": "Студент"},
            "next_lesson": {"subject": "Линейная алгебра", "room": "218", "old_room": "304",
                            "teacher": "Анна Соколова", "starts_at": starts,
                            "ends_at": starts + timedelta(minutes=90), "detail_url": lesson_url},
            "next_deadline": {"title": "Сдать задачи", "due_at": starts, "target_url": reverse("study")},
            "changes": [{"title": "Перенос пары", "body": "Новая аудитория", "target_url": lesson_url}],
        })
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
            page = browser.new_page(viewport={"width": 360, "height": 740})
            page.goto(self.live_server_url + reverse("login"))
            page.set_content(html)
            expect(page.get_by_text("Теперь 218")).to_be_visible()
            expect(page.locator(".move")).to_contain_text("Была 304")
            for label in ("Линейная алгебра", "Перенос пары"):
                expect(page.get_by_role("link", name=label)).to_have_attribute("href", lesson_url)
            expect(page.get_by_role("link", name="Сдать задачи")).to_have_attribute("href", reverse("study"))
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), 360)
            browser.close()
