// Apply the stored choice before the stylesheets paint the page.
(() => {
  const key = "dean-theme";
  const choices = ["system", "light", "dark"];
  const apply = value => {
    document.documentElement.style.colorScheme = value === "system" ? "light dark" : value;
  };
  let current = "system";
  let palette = "ocean";
  try {
    if (localStorage.getItem("dean-rail") === "compact") document.documentElement.dataset.rail = "compact";
    const saved = localStorage.getItem(key);
    if (choices.includes(saved)) current = saved;
    if (["ocean", "sage", "amber"].includes(localStorage.getItem("dean-palette"))) palette = localStorage.getItem("dean-palette");
  } catch {} // The selector still works when storage is unavailable.
  apply(current);
  document.documentElement.dataset.palette = palette;
  document.addEventListener("DOMContentLoaded", () => {
    const picker = document.querySelector(".theme-picker");
    const popover = picker.querySelector("[popover]");
    const trigger = picker.querySelector(".theme-trigger");
    const options = picker.querySelectorAll("[data-theme]");
    const palettes = picker.querySelectorAll("[data-palette]");
    const paletteGroup = picker.querySelector(".palette-options");
    function display(value) {
      for (const option of options) {
        const selected = option.dataset.theme === value;
        option.setAttribute("aria-pressed", String(selected));
        if (selected) trigger.querySelector("span").textContent = option.textContent;
      }
    }
    display(current);
    const displayPalette = () => {
      paletteGroup.hidden = current === "light" || (current === "system" && !matchMedia("(prefers-color-scheme: dark)").matches);
      palettes.forEach(option => option.setAttribute("aria-pressed", String(option.dataset.palette === palette)));
    };
    displayPalette();
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", displayPalette);
    picker.hidden = false;
    for (const option of options) {
      option.addEventListener("click", () => {
        current = option.dataset.theme;
        apply(current);
        display(current);
        displayPalette();
        try { localStorage.setItem(key, current); } catch {}
        popover.hidePopover();
        trigger.focus();
      });
    }
    for (const option of palettes) option.addEventListener("click", () => {
      palette = option.dataset.palette;
      document.documentElement.dataset.palette = palette;
      displayPalette();
      try { localStorage.setItem("dean-palette", palette); } catch {}
      popover.hidePopover();
      trigger.focus();
    });
    popover.addEventListener("toggle", event => {
      if (event.newState === "open") {
        const rect = trigger.getBoundingClientRect();
        popover.style.top = (rect.bottom + 6) + "px";
        popover.style.right = (document.documentElement.clientWidth - rect.right) + "px";
      }
    });
  });
})();
