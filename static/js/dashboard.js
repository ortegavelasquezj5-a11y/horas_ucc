/*
 * Dashboard · gráficas con Chart.js.
 * Los datos los entrega Django en <script id="datos-graficas" type="application/json">
 * (filtro json_script), así que siempre reflejan la base de datos y el programa elegido.
 */
"use strict";

(() => {
  const nodo = document.getElementById("datos-graficas");
  if (!nodo || typeof Chart === "undefined") return;
  const datos = JSON.parse(nodo.textContent);

  const AZUL = "#003865", VERDE = "#00843D", AMBAR = "#E0A100", ROJO = "#C0392B";
  const PALETA = [AZUL, VERDE, "#2E86C1", AMBAR, "#7D3C98", "#16A085", "#CA6F1E"];

  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = "#5A6675";
  Chart.defaults.plugins.legend.labels.usePointStyle = true;

  const horas = (v) => `${Number(v).toLocaleString("es-CO", { maximumFractionDigits: 1 })} h`;
  const vacio = (serie) => !serie.valores.length || serie.valores.every((v) => v === 0);

  function sinDatos(id) {
    const lienzo = document.getElementById(id);
    lienzo.replaceWith(Object.assign(document.createElement("p"), {
      className: "texto-suave mb-0", textContent: "Aún no hay datos para esta gráfica.",
    }));
  }

  function grafica(id, config, serie) {
    if (serie && vacio(serie)) return sinDatos(id);
    return new Chart(document.getElementById(id), config);
  }

  // 1. Horas aprobadas por tipo (barras horizontales)
  grafica("grafica-tipo", {
    type: "bar",
    data: { labels: datos.porTipo.etiquetas,
            datasets: [{ data: datos.porTipo.valores, backgroundColor: PALETA, borderRadius: 6 }] },
    options: { indexAxis: "y", maintainAspectRatio: false,
               plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => horas(c.raw) } } },
               scales: { x: { beginAtZero: true, ticks: { callback: horas } }, y: { grid: { display: false } } } },
  }, datos.porTipo);

  // 2. Horas aprobadas por mes (línea con área)
  grafica("grafica-mes", {
    type: "line",
    data: { labels: datos.porMes.etiquetas,
            datasets: [{ data: datos.porMes.valores, borderColor: AZUL, backgroundColor: "rgba(0,56,101,.12)",
                         fill: true, cubicInterpolationMode: "monotone", pointRadius: 4, pointHoverRadius: 7 }] },
    options: { maintainAspectRatio: false,
               plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => horas(c.raw) } } },
               scales: { y: { beginAtZero: true, ticks: { callback: horas } }, x: { grid: { display: false } } } },
  }, datos.porMes);

  // 3. Cumplimiento de la meta (dona) con el porcentaje en el centro
  const total = datos.cumplimiento.valores.reduce((a, b) => a + b, 0);
  const textoCentro = {
    id: "textoCentro",
    afterDraw(chart) {
      const { ctx, chartArea: { left, right, top, bottom } } = chart;
      const cumplen = total ? Math.round((datos.cumplimiento.valores[0] / total) * 100) : 0;
      ctx.save();
      ctx.textAlign = "center";
      ctx.fillStyle = AZUL;
      ctx.font = `700 26px ${Chart.defaults.font.family}`;
      ctx.fillText(`${cumplen} %`, (left + right) / 2, (top + bottom) / 2 + 4);
      ctx.font = `12px ${Chart.defaults.font.family}`;
      ctx.fillStyle = "#5A6675";
      ctx.fillText("cumplen", (left + right) / 2, (top + bottom) / 2 + 22);
      ctx.restore();
    },
  };
  grafica("grafica-cumplimiento", {
    type: "doughnut",
    data: { labels: datos.cumplimiento.etiquetas,
            datasets: [{ data: datos.cumplimiento.valores, backgroundColor: [VERDE, AMBAR, ROJO], borderWidth: 2 }] },
    options: { maintainAspectRatio: false, cutout: "68%",
               plugins: { legend: { position: "bottom" },
                          tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.raw} estudiante(s)` } } } },
    plugins: [textoCentro],
  }, datos.cumplimiento);

  // 4. Promedio por estudiante vs. meta, por programa
  grafica("grafica-programa", {
    type: "bar",
    data: { labels: datos.porPrograma.etiquetas,
            datasets: [
              { label: "Promedio por estudiante", data: datos.porPrograma.promedio, backgroundColor: AZUL, borderRadius: 6 },
              { label: "Meta del programa", data: datos.porPrograma.meta, backgroundColor: "rgba(0,132,61,.25)",
                borderColor: VERDE, borderWidth: 2, borderRadius: 6 },
            ] },
    options: { maintainAspectRatio: false,
               plugins: { tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${horas(c.raw)}` } } },
               scales: { y: { beginAtZero: true, ticks: { callback: horas } }, x: { grid: { display: false } } } },
  }, { valores: datos.porPrograma.meta });
})();