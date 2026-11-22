const planner = document.querySelector(".goal-planner");
if (planner) {
  const target = planner.querySelector("#goal-target");
  const value = planner.querySelector("#goal-value");
  const answer = planner.querySelector(".goal-answer");
  const next = planner.querySelector(".goal-next");
  const chart = planner.querySelector(".goal-chart");
  const points = Number(planner.dataset.points);
  const remaining = Number(planner.dataset.remaining);
  const maximum = Number(planner.dataset.maximum);
  const update = () => {
    const goal = Number(target.value);
    const needed = Math.max(0, Math.ceil(goal * maximum / 10 - points));
    chart.style.setProperty("--earned", `${Math.min(100, points / maximum * 100)}%`);
    chart.style.setProperty("--possible", `${Math.min(100, (points + remaining) / maximum * 100)}%`);
    chart.style.setProperty("--target", `${goal * 10}%`);
    value.value = String(goal);
    if (needed === 0) {
      answer.textContent = `Цель ${goal} из 10 уже достигнута по опубликованным заданиям.`;
      next.textContent = "Можно проверить итог в ведомости или выбрать более высокую цель.";
    } else if (needed > remaining) {
      answer.textContent = `Для ${goal} из 10 нужно ещё ${needed} баллов. По оставшимся заданиям доступно ${remaining} — этой цели пока не достичь.`;
      next.textContent = `Максимум при выполнении всех оставшихся заданий — ${((points + remaining) * 10 / maximum).toFixed(1)} из 10.`;
    } else {
      answer.textContent = `Для ${goal} из 10 нужно ещё ${needed} из ${remaining} доступных баллов.`;
      next.textContent = `Следующий шаг: открыть задания курса и набрать минимум ${needed} баллов.`;
    }
  };
  target.addEventListener("input", update);
  update();
}
