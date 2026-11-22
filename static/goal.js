const planner = document.querySelector(".goal-planner");
if (planner) {
  const target = planner.querySelector("#goal-target");
  const value = planner.querySelector("#goal-value");
  const answer = planner.querySelector(".goal-answer");
  const points = Number(planner.dataset.points);
  const remaining = Number(planner.dataset.remaining);
  const maximum = Number(planner.dataset.maximum);
  const update = () => {
    const goal = Number(target.value);
    const needed = Math.max(0, Math.ceil(goal * maximum / 10 - points));
    value.value = String(goal);
    if (needed === 0) answer.textContent = `Цель ${goal} из 10 уже достигнута по опубликованным заданиям.`;
    else if (needed > remaining) answer.textContent = `Для ${goal} из 10 нужно ещё ${needed} баллов. По оставшимся заданиям доступно ${remaining} — этой цели пока не достичь.`;
    else answer.textContent = `Для ${goal} из 10 нужно ещё ${needed} из ${remaining} доступных баллов.`;
  };
  target.addEventListener("input", update);
  update();
}
