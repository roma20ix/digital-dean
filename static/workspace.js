const week = document.querySelector(".week-grid");
const route = document.querySelector(".day-route");
if (route) {
  const stops = [...route.querySelectorAll("[data-route-stop]")];
  const previews = [...route.querySelectorAll("[data-route-preview]")];
  const show = index => {
    stops.forEach((stop, i) => stop.classList.toggle("is-active", i === index));
    previews.forEach((preview, i) => {
      preview.hidden = i !== index;
      preview.classList.toggle("is-active", i === index);
    });
  };
  stops.forEach((stop, index) => {
    stop.addEventListener("pointerenter", () => show(index));
    stop.addEventListener("focus", () => show(index));
  });
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    route.addEventListener("pointermove", event => {
      const rect = route.getBoundingClientRect();
      route.style.setProperty("--route-x", `${event.clientX - rect.left}px`);
      route.style.setProperty("--route-y", `${event.clientY - rect.top}px`);
    });
    route.addEventListener("pointerleave", () => {
      route.style.removeProperty("--route-x");
      route.style.removeProperty("--route-y");
    });
  }
}
const snowToggle = document.querySelector(".snow-toggle");
if (snowToggle) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let enabled = false;
  try { enabled = localStorage.getItem("dean-snow") === "on"; } catch {}
  let layer;
  const renderSnow = () => {
    snowToggle.hidden = false;
    snowToggle.setAttribute("aria-pressed", String(enabled));
    snowToggle.setAttribute("aria-label", enabled ? "Выключить снег" : "Включить снег");
    snowToggle.title = enabled ? "Выключить снег" : "Включить снег";
    layer?.remove();
    layer = null;
    if (!enabled || reduced.matches) return;
    layer = document.createElement("div");
    layer.className = "snow-layer";
    layer.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 28; i++) {
      const flake = document.createElement("span");
      flake.className = "snowflake";
      flake.style.cssText = `--x:${(i * 37) % 100}%;--size:${2 + (i % 4)}px;--duration:${9 + (i % 7)}s;--delay:-${(i * 13) % 17}s;--drift:${(i % 2 ? 1 : -1) * (12 + i)}px`;
      layer.append(flake);
    }
    document.body.append(layer);
  };
  snowToggle.addEventListener("click", () => {
    enabled = !enabled;
    try { localStorage.setItem("dean-snow", enabled ? "on" : "off"); } catch {}
    renderSnow();
  });
  reduced.addEventListener("change", renderSnow);
  renderSnow();
}
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
    if (event.target !== drawer) return;
    const {left, right, top, bottom} = drawer.getBoundingClientRect();
    if (event.clientX < left || event.clientX > right || event.clientY < top || event.clientY > bottom) {
      drawer.close();
    }
  });
}

const mobileMenu = document.querySelector(".menu");
if (mobileMenu) {
  document.addEventListener("click", event => {
    if (mobileMenu.open && !mobileMenu.contains(event.target)) mobileMenu.open = false;
  });
  mobileMenu.addEventListener("keydown", event => {
    if (event.key === "Escape" && mobileMenu.open) {
      mobileMenu.open = false;
      mobileMenu.querySelector("summary").focus();
    }
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
