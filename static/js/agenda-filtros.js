const filtrosAgenda = document.querySelector("#agenda-filtros");
const seletorTipos = document.querySelector("#filtro-tipos");
const resumoTipos = document.querySelector("#filtro-tipos-resumo");
const botaoLimparFiltro = document.querySelector("#agenda-limpar-filtro");
let filtroAplicado = !botaoLimparFiltro.disabled;
let consultaAgenda;

// A entrada inicial precisa da data exibida para o botão Voltar recuperá-la.
const urlInicialAgenda = new URL(window.location.href);
const dataInicialAgenda = filtrosAgenda.elements.data.value;
if (urlInicialAgenda.searchParams.get("data") !== dataInicialAgenda) {
    urlInicialAgenda.searchParams.set("data", dataInicialAgenda);
    window.history.replaceState(window.history.state, "", urlInicialAgenda);
}

async function atualizarAgenda(url, { ancora = filtrosAgenda, historico } = {}) {
    consultaAgenda?.abort();
    const controle = new AbortController();
    consultaAgenda = controle;

    const resposta = await fetch(url, {
        cache: "no-store",
        signal: controle.signal,
    });
    if (!resposta.ok) {
        throw new Error("Não foi possível consultar a agenda.");
    }

    const pagina = new DOMParser().parseFromString(await resposta.text(), "text/html");
    controle.signal.throwIfAborted();
    const novosFiltros = pagina.querySelector("#agenda-filtros");
    if (!novosFiltros) {
        throw new Error("A resposta não contém a agenda.");
    }

    const topo = ancora.getBoundingClientRect().top;
    const grade = document.querySelector("#agenda-horarios .calendar-scroll");
    const novaGrade = pagina.querySelector("#agenda-horarios .calendar-scroll");
    const subtitulo = document.querySelector("#agenda-horarios .calendar-subbar");
    subtitulo.replaceChildren(...pagina.querySelector(".calendar-subbar").childNodes);

    if (novaGrade) {
        if (grade) {
            const { scrollLeft, scrollTop } = grade;
            grade.replaceWith(novaGrade);
            novaGrade.scrollTo(scrollLeft, scrollTop);
        } else {
            subtitulo.after(novaGrade);
        }
    } else {
        grade?.remove();
    }

    document.querySelector(".room-grid").replaceWith(pagina.querySelector(".room-grid"));
    const sala = document.querySelector("#reserva-sala");
    const salaSelecionada = sala.value;
    sala.replaceChildren(...pagina.querySelector("#reserva-sala").options);
    if (Array.from(sala.options).some((opcao) => opcao.value === salaSelecionada)) {
        sala.value = salaSelecionada;
    }

    resumoTipos.textContent = novosFiltros.querySelector("#filtro-tipos-resumo").textContent;
    const novasOpcoes = novosFiltros.querySelector("#filtro-tipos-opcoes");
    // O Chromium pode deixar as opções invisíveis ao trocar só os filhos do fieldset fechado.
    seletorTipos.querySelector("#filtro-tipos-opcoes").replaceWith(document.importNode(novasOpcoes, true));
    const limparEstavaEmFoco = document.activeElement === botaoLimparFiltro;
    filtroAplicado = !novosFiltros.querySelector("#agenda-limpar-filtro").disabled;
    botaoLimparFiltro.disabled = !filtroAplicado;
    if (limparEstavaEmFoco && botaoLimparFiltro.disabled) {
        seletorTipos.querySelector("summary").focus({ preventScroll: true });
    }
    const data = novosFiltros.elements.data.value;
    filtrosAgenda.elements.data.value = data;
    document.querySelector("#reserva-data").value = data;

    url.searchParams.set("data", data);
    if (historico && url.href !== window.location.href) {
        window.history[historico](window.history.state, "", url);
    }

    window.scrollBy({ top: ancora.getBoundingClientRect().top - topo, behavior: "instant" });
}

async function consultarAgenda(url, historico) {
    try {
        await atualizarAgenda(url, { historico });
    } catch (erro) {
        if (erro.name !== "AbortError") {
            avisosSistema.mostrar("Não foi possível consultar a agenda. Tente novamente.", "error");
        }
    }
}

filtrosAgenda.addEventListener("submit", (event) => {
    event.preventDefault();
    seletorTipos.open = false;
    const limparTipos = event.submitter === botaoLimparFiltro;
    const url = new URL(window.location.href);
    url.searchParams.delete("tipo");
    url.searchParams.delete("data");
    url.searchParams.delete("limpar_tipos");
    url.searchParams.delete("filtro_tipos");
    for (const [nome, valor] of new FormData(filtrosAgenda, event.submitter)) {
        if (valor && !(limparTipos && nome === "tipo")) {
            url.searchParams.append(nome, valor);
        }
    }
    consultarAgenda(url, "pushState");
});

seletorTipos.addEventListener("change", () => {
    const tipos = new FormData(filtrosAgenda).getAll("tipo");
    botaoLimparFiltro.disabled = !filtroAplicado && tipos.length === 0;
    switch (tipos.length) {
        case 0:
            resumoTipos.textContent = "Todos os tipos";
            break;
        case 1:
            resumoTipos.textContent = tipos[0];
            break;
        default:
            resumoTipos.textContent = `${tipos.length} tipos`;
    }
});

document.addEventListener("click", (event) => {
    if (seletorTipos.open && !seletorTipos.contains(event.target)) {
        seletorTipos.open = false;
    }
});

seletorTipos.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && seletorTipos.open) {
        seletorTipos.open = false;
        seletorTipos.querySelector("summary").focus({ preventScroll: true });
    }
});

window.addEventListener("popstate", () => {
    consultarAgenda(new URL(window.location.href));
});
