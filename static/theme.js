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
    const select = document.querySelector("#theme-choice");
    select.value = current;
    select.parentElement.hidden = false;
    select.addEventListener("change", () => {
      apply(select.value);
      try { localStorage.setItem(key, select.value); } catch {}
    });
  });
})();
