/*
 * Horas UCC · interactividad del lado del cliente.
 *
 * Módulos (cada uno se activa solo si la página tiene los elementos que usa):
 *   1. Avisos flotantes (toasts)           -> aviso(texto, tipo)
 *   2. Confirmación con modal              -> [data-confirmar] en form o button
 *   3. Envío automático de filtros         -> select[data-autoenviar]
 *   4. Validación de formularios           -> form[data-validar]
 *   5. Validación de la revisión de horas  -> form[data-revision]
 *   6. Catálogo: búsqueda en vivo (fetch) e inscripción sin recargar
 *   7. Detalles: cierre automático de alertas, botón imprimir
 */
"use strict";

/* ------------------------------------------------------------ utilidades */
const $ = (selector, raiz = document) => raiz.querySelector(selector);
const $$ = (selector, raiz = document) => [...raiz.querySelectorAll(selector)];

function leerCookie(nombre) {
  const fila = document.cookie.split("; ").find((c) => c.startsWith(nombre + "="));
  return fila ? decodeURIComponent(fila.split("=")[1]) : "";
}

function retrasar(funcion, ms) {
  let temporizador;
  return (...args) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => funcion(...args), ms);
  };
}

/* ------------------------------------------------- 1. avisos flotantes */
function aviso(texto, tipo = "success") {
  const contenedor = $("#avisos");
  if (!contenedor) return;
  const toast = document.createElement("div");
  toast.className = `toast align-items-center border-0 text-bg-${tipo}`;
  toast.setAttribute("role", "status");
  toast.innerHTML = `<div class="d-flex"><div class="toast-body"></div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button></div>`;
  toast.querySelector(".toast-body").textContent = texto; // textContent: evita inyectar HTML
  contenedor.appendChild(toast);
  toast.addEventListener("hidden.bs.toast", () => toast.remove());
  new bootstrap.Toast(toast, { delay: 4500 }).show();
}

/* ------------------------------------------ 2. confirmación con modal */
const confirmar = (() => {
  let modal, instancia, resolver;

  function crear() {
    modal = document.createElement("div");
    modal.className = "modal fade";
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog modal-dialog-centered"><div class="modal-content">
        <div class="modal-header"><h2 class="modal-title h5 fw-bold">Confirmar acción</h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button></div>
        <div class="modal-body"><p class="mb-0" data-texto></p></div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Volver</button>
          <button type="button" class="btn" data-aceptar>Sí, continuar</button>
        </div></div></div>`;
    document.body.appendChild(modal);
    instancia = new bootstrap.Modal(modal);
    $("[data-aceptar]", modal).addEventListener("click", () => { resolver(true); resolver = null; instancia.hide(); });
    modal.addEventListener("hidden.bs.modal", () => { if (resolver) resolver(false); resolver = null; });
  }

  // Devuelve una promesa: true si el usuario acepta
  return (texto, peligro = false) => {
    if (!modal) crear();
    $("[data-texto]", modal).textContent = texto;
    $("[data-aceptar]", modal).className = `btn ${peligro ? "btn-danger" : "btn-ucc"}`;
    instancia.show();
    return new Promise((ok) => { resolver = ok; });
  };
})();

// El evento submit se intercepta en fase de captura para preguntar antes de enviar.
document.addEventListener("submit", async (evento) => {
  const form = evento.target;
  const boton = evento.submitter;
  const origen = boton?.dataset.confirmar ? boton : form.dataset.confirmar ? form : null;
  if (!origen || form.dataset.confirmado) return;
  evento.preventDefault();
  evento.stopImmediatePropagation();
  // Si el formulario tiene errores, se muestran antes de preguntar
  if (form.antesDeConfirmar && !form.antesDeConfirmar(boton)) return;
  if (!(await confirmar(origen.dataset.confirmar, "peligro" in origen.dataset))) return;
  form.dataset.confirmado = "1";
  form.requestSubmit(boton); // vuelve a enviar (y pasa por las validaciones / el fetch)
  delete form.dataset.confirmado;
}, true);

/* --------------------------------------------- 3. filtros automáticos */
$$("select[data-autoenviar]").forEach((select) =>
  select.addEventListener("change", () => select.form.requestSubmit())
);

// Buscadores de reportes: envían el filtro 500 ms después de dejar de escribir
$$("input[data-buscar-auto]").forEach((campo) => {
  campo.addEventListener("input", retrasar(() => campo.form.requestSubmit(), 500));
  if (campo.value) { campo.focus(); campo.setSelectionRange(campo.value.length, campo.value.length); }
});

/* ------------------------------------------- 4. validación del cliente */
const EXTENSIONES = { ".pdf": true, ".jpg": true, ".jpeg": true, ".png": true };

function mensajeDeError(campo) {
  const v = campo.validity;
  if (v.valueMissing) return "Este campo es obligatorio.";
  if (v.rangeUnderflow) return `El valor mínimo es ${campo.min}.`;
  if (v.rangeOverflow) {
    return campo.type === "date" ? "La fecha no puede ser futura." : `El valor máximo es ${campo.max}.`;
  }
  if (v.stepMismatch) return `Usa múltiplos de ${campo.step}.`;
  if (v.typeMismatch) return "El formato no es válido.";
  if (v.tooLong) return `Máximo ${campo.maxLength} caracteres.`;
  if (v.customError) return campo.validationMessage;
  return "";
}

function validarArchivo(campo) {
  campo.setCustomValidity("");
  const archivo = campo.files?.[0];
  if (!archivo) return;
  const extension = archivo.name.slice(archivo.name.lastIndexOf(".")).toLowerCase();
  const maxMb = Number(campo.dataset.maxMb || 5);
  if (!EXTENSIONES[extension]) campo.setCustomValidity("Solo se aceptan archivos PDF, JPG o PNG.");
  else if (archivo.size > maxMb * 1024 * 1024) {
    campo.setCustomValidity(`El archivo pesa ${(archivo.size / 1048576).toFixed(1)} MB; el máximo es ${maxMb} MB.`);
  }
}

function validarRangoFechas(campo) {
  // <input data-despues-de="id_otro">: la fecha no puede ser anterior a la del otro campo
  const otro = document.getElementById(campo.dataset.despuesDe);
  campo.setCustomValidity("");
  if (otro && campo.value && otro.value && campo.value < otro.value) {
    campo.setCustomValidity("La fecha de fin no puede ser anterior a la de inicio.");
  }
}

function pintarEstado(campo) {
  if (campo.type === "file") validarArchivo(campo);
  if (campo.dataset.despuesDe) validarRangoFechas(campo);
  const contenedor = campo.closest(".mb-3") || campo.parentElement;
  let caja = $(".invalid-feedback", contenedor);
  if (!caja) {
    caja = document.createElement("div");
    caja.className = "invalid-feedback";
    campo.insertAdjacentElement("afterend", caja);
  }
  const error = mensajeDeError(campo);
  caja.textContent = error;
  campo.classList.toggle("is-invalid", Boolean(error));
  campo.classList.toggle("is-valid", !error && campo.value !== "");
  return !error;
}

$$("form[data-validar]").forEach((form) => {
  const campos = $$("input:not([type=hidden]), select, textarea", form);
  campos.forEach((campo) => {
    // Primero valida al salir del campo; después de un error, valida mientras escribe
    campo.addEventListener("blur", () => pintarEstado(campo));
    campo.addEventListener("input", () => { if (campo.classList.contains("is-invalid")) pintarEstado(campo); });
    campo.addEventListener("change", () => pintarEstado(campo));
  });
  form.addEventListener("submit", (evento) => {
    const malos = campos.filter((c) => !pintarEstado(c));
    if (malos.length) {
      evento.preventDefault();
      malos[0].focus();
      aviso("Revisa los campos marcados en rojo.", "danger");
    }
  });

  // Vista previa del archivo elegido
  $$("input[type=file]", form).forEach((campo) =>
    campo.addEventListener("change", () => {
      const archivo = campo.files?.[0];
      let info = $(".info-archivo", campo.parentElement);
      if (!info) {
        info = document.createElement("div");
        info.className = "info-archivo small mt-1 texto-suave";
        campo.parentElement.appendChild(info);
      }
      info.textContent = archivo && campo.validity.valid
        ? `📎 ${archivo.name} · ${(archivo.size / 1024).toFixed(0)} KB`
        : "";
    })
  );
});

/* ------------------------------- 5. revisión de horas (Bienestar) */
$$("form[data-revision]").forEach((form) => {
  const horas = $("[name=horas]", form);
  const motivo = $("[name=motivo]", form);
  const solicitadas = parseFloat((form.dataset.horasSolicitadas || "0").replace(",", "."));

  // Contador de caracteres del motivo
  const contador = document.createElement("div");
  contador.className = "form-text text-end";
  motivo.insertAdjacentElement("afterend", contador);
  const contar = () => { contador.textContent = `${motivo.value.trim().length} caracteres`; };
  motivo.addEventListener("input", contar);
  contar();

  // Si cambia las horas, avisa que el motivo pasa a ser obligatorio
  horas?.addEventListener("input", () => {
    const ajusta = horas.value !== "" && parseFloat(horas.value) !== solicitadas;
    motivo.placeholder = ajusta ? "Obligatorio: explica por qué ajustas las horas" : "Ej.: el soporte no indica la intensidad horaria";
  });

  function revisar(boton) {
    const accion = boton?.value;
    const ajusta = horas && horas.value !== "" && parseFloat(horas.value) !== solicitadas;
    let error = "";
    if ((accion === "rechazar" || ajusta) && motivo.value.trim().length < 5) {
      error = accion === "rechazar" ? "Escribe el motivo del rechazo (mínimo 5 caracteres)."
                                    : "Escribe por qué ajustas las horas (mínimo 5 caracteres).";
    } else if (horas && horas.value !== "" && (horas.value < 0.5 || horas.value > 40)) {
      error = "Las horas deben estar entre 0,5 y 40.";
    }
    if (error) {
      motivo.classList.add("is-invalid");
      motivo.focus();
      aviso(error, "danger");
    }
    return !error;
  }
  form.antesDeConfirmar = revisar;
  form.addEventListener("submit", (evento) => {
    if (!revisar(evento.submitter)) evento.preventDefault();
  });
  motivo.addEventListener("input", () => motivo.classList.remove("is-invalid"));
});

/* ------------------- 6. catálogo: búsqueda en vivo e inscripción AJAX */
const filtros = $("#filtros-catalogo");
const resultados = $("#catalogo-resultados");

if (filtros && resultados) {
  const buscador = $("[name=q]", filtros);
  const tipo = $("[name=tipo]", filtros);
  const cargando = $("#catalogo-cargando");
  $$(".js-ocultar", filtros).forEach((b) => b.classList.add("d-none")); // con JS el botón sobra

  async function cargar(url = null) {
    const parametros = new URLSearchParams();
    if (buscador.value.trim()) parametros.set("q", buscador.value.trim());
    if (tipo.value) parametros.set("tipo", tipo.value);
    const destino = url || `${location.pathname}?${parametros}`;
    cargando.classList.remove("d-none");
    resultados.classList.add("cargando");
    try {
      const respuesta = await fetch(destino, { headers: { "X-Requested-With": "fetch" } });
      if (!respuesta.ok) throw new Error(respuesta.status);
      resultados.innerHTML = await respuesta.text();
      history.replaceState(null, "", destino); // la URL queda compartible
    } catch {
      aviso("No se pudo cargar el catálogo. Revisa tu conexión.", "danger");
    } finally {
      cargando.classList.add("d-none");
      resultados.classList.remove("cargando");
    }
  }

  buscador.addEventListener("input", retrasar(() => cargar(), 300));
  filtros.addEventListener("submit", (e) => { e.preventDefault(); cargar(); });

  $$(".chip-tipo", filtros).forEach((chip) =>
    chip.addEventListener("click", (e) => {
      e.preventDefault();
      tipo.value = chip.dataset.tipo;
      $$(".chip-tipo", filtros).forEach((c) => {
        const activo = c === chip;
        c.classList.toggle("btn-primary", activo);
        c.classList.toggle("btn-outline-secondary", !activo);
      });
      cargar();
    })
  );

  // Paginación sin recargar
  resultados.addEventListener("click", (e) => {
    const enlace = e.target.closest(".pagination a");
    if (!enlace) return;
    e.preventDefault();
    cargar(enlace.href);
    filtros.scrollIntoView({ behavior: "smooth" });
  });

  // Inscribirse / cancelar sin recargar la página
  resultados.addEventListener("submit", async (e) => {
    const form = e.target.closest("form[data-ajax]");
    if (!form) return;
    e.preventDefault();
    const boton = $("button", form);
    boton.disabled = true;
    boton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Procesando…';
    try {
      const respuesta = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "fetch", "X-CSRFToken": leerCookie("csrftoken") },
      });
      const datos = await respuesta.json();
      aviso(datos.mensaje, datos.ok ? "success" : "danger");
    } catch {
      aviso("No se pudo completar la acción. Intenta de nuevo.", "danger");
    }
    await cargar(location.pathname + location.search); // refresca cupos y botones
  });
}

/* ------------------------------------------------------- 7. detalles */
// Las alertas de éxito se cierran solas a los 6 segundos
$$(".alert-success.alert-dismissible").forEach((alerta) =>
  setTimeout(() => bootstrap.Alert.getOrCreateInstance(alerta).close(), 6000)
);

$$("[data-imprimir]").forEach((b) => b.addEventListener("click", () => window.print()));

// Aparición suave de las tarjetas al hacer scroll
if ("IntersectionObserver" in window) {
  const observador = new IntersectionObserver((entradas) =>
    entradas.forEach((entrada) => {
      if (entrada.isIntersecting) {
        entrada.target.classList.add("visible");
        observador.unobserve(entrada.target);
      }
    }), { threshold: 0.08 });
  const observar = () => $$(".tarjeta:not(.animada)").forEach((t) => { t.classList.add("animada"); observador.observe(t); });
  observar();
  if (resultados) new MutationObserver(observar).observe(resultados, { childList: true });
}
