// Apply the stored choice before the stylesheets paint the page.
(() => {
  const key = "dean-theme";
  const choices = ["system", "light", "dark"];
  const apply = value => {
    document.documentElement.style.colorScheme = value === "system" ? "light dark" : value;
  };
  let current = "system";
  try {
    const saved = localStorage.getItem(key);
    if (choices.includes(saved)) current = saved;
  } catch {} // The selector still works when storage is unavailable.
  apply(current);
  document.addEventListener("DOMContentLoaded", () => {
    const picker = document.querySelector(".theme-picker");
    const popover = picker.querySelector("[popover]");
    const trigger = picker.querySelector(".theme-trigger");
    const options = picker.querySelectorAll("[data-theme]");
    function display(value) {
      for (const option of options) {
        const selected = option.dataset.theme === value;
        option.setAttribute("aria-pressed", String(selected));
        if (selected) trigger.querySelector("span").textContent = option.textContent;
      }
    }
    display(current);
    picker.hidden = false;
    for (const option of options) {
      option.addEventListener("click", () => {
        current = option.dataset.theme;
        apply(current);
        display(current);
        try { localStorage.setItem(key, current); } catch {}
        popover.hidePopover();
        trigger.focus();
      });
    }
    popover.addEventListener("toggle", event => {
      if (event.newState === "open") {
        const rect = trigger.getBoundingClientRect();
        popover.style.top = (rect.bottom + 6) + "px";
        popover.style.right = (document.documentElement.clientWidth - rect.right) + "px";
      }
    });
  });
})();
