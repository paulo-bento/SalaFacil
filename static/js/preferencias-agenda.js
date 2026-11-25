const campoTiposPreferidos = document.querySelector(".preferencias-agenda-tipos");
const todosTiposPreferidos = campoTiposPreferidos.querySelector("[name=todos_tipos]");
const tiposPreferidos = Array.from(campoTiposPreferidos.querySelectorAll("[name=tipos_sala_preferidos]"));

campoTiposPreferidos.addEventListener("change", (event) => {
    if (event.target === todosTiposPreferidos) {
        if (todosTiposPreferidos.checked) {
            tiposPreferidos.forEach((tipo) => { tipo.checked = false; });
        }
    } else {
        todosTiposPreferidos.checked = !tiposPreferidos.some((tipo) => tipo.checked);
    }
});
