const week = document.querySelector(".week-grid");
if (week) {
  // Give matching start times a shared row, including mixed-duration classes.
  const periods = Array.from(week.querySelectorAll(".period"));
  const slots = [...new Set(periods.map(period => period.dataset.start))].sort();
  const label = (text, row) => {
    const time = document.createElement("span");
    time.className = "axis";
    time.textContent = text;
    time.style.gridRow = row;
    week.append(time);
  };
  label("МСК", 1);
  slots.forEach((slot, index) => label(slot, index + 2));
  week.querySelectorAll(".day").forEach(day => {
    for (const element of day.children) {
      element.style.gridColumn = Number(day.dataset.column) + 1;
      element.style.gridRow = element.matches("h2") ? 1 :
        element.matches(".period") ? slots.indexOf(element.dataset.start) + 2 : 2;
    }
  });
  week.classList.add("aligned");
}

const bell = document.querySelector(".bell");
if (bell) {
  const drawer = document.querySelector(".drawer");
  const content = drawer.querySelector(".drawer-content");
  bell.addEventListener("click", async event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault();
    drawer.showModal();
    content.textContent = "Загружаем уведомления…";
    try {
      const csrf = document.querySelector('form input[name="csrfmiddlewaretoken"]').value;
      const response = await fetch(bell.dataset.panel, {
        method: "POST", headers: {"X-CSRFToken": csrf}, mode: "same-origin"
      });
      if (!response.ok || response.redirected) throw new Error();
      content.innerHTML = await response.text();
      bell.querySelector("i")?.remove();
      bell.setAttribute("aria-label", "Открыть уведомления");
      if (document.querySelector(".notice")) {
        drawer.addEventListener("close", () => location.reload(), {once: true});
      }
    } catch {
      content.textContent = "Не удалось загрузить уведомления. Откройте полную ленту.";
    }
  });
  drawer.addEventListener("click", event => {
    if (event.target === drawer && event.clientX < drawer.getBoundingClientRect().left) drawer.close();
  });
}

const railToggle = document.querySelector(".rail-toggle");
if (railToggle) {
  const root = document.documentElement;
  const syncRail = () => {
    const compact = root.dataset.rail === "compact";
    const label = compact ? "Развернуть меню" : "Свернуть меню";
    railToggle.setAttribute("aria-expanded", String(!compact));
    railToggle.setAttribute("aria-label", label);
    railToggle.title = label;
  };
  syncRail();
  railToggle.hidden = false;
  railToggle.addEventListener("click", () => {
    root.dataset.rail = root.dataset.rail === "compact" ? "wide" : "compact";
    syncRail();
    try { localStorage.setItem("dean-rail", root.dataset.rail); } catch {}
  });
}
