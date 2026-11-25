const painelNotificacoes = document.querySelector(".notificacoes-card");
let leituraEmAndamento = false;
let listaPendente = false;
let consultaLista;

function marcarItemLido(item) {
    item.classList.remove("notificacao-nova");
    item.querySelector(".notificacao-form").remove();
    const estado = item.querySelector(".notificacao-leitura");
    estado.textContent = "Lida";
    estado.tabIndex = -1;
    return estado;
}

painelNotificacoes?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formulario = event.target;
    const botao = formulario.querySelector("button");
    if (botao.disabled) {
        return;
    }

    const formularioTodas = painelNotificacoes.querySelector("#notificacoes-ler-todas");
    const botaoTodas = formularioTodas.querySelector("button");
    const todas = formulario === formularioTodas;
    const item = formulario.closest(".notificacao");
    const botoes = painelNotificacoes.querySelectorAll("form button:enabled");
    botoes.forEach((controle) => { controle.disabled = true; });
    let resultado;
    leituraEmAndamento = true;
    consultaLista?.abort();

    try {
        const resposta = await fetch(formulario.action, {
            method: "POST",
            headers: { Accept: "application/json" },
            body: new FormData(formulario),
            credentials: "same-origin",
        });
        if (!resposta.ok) {
            throw new Error("Não foi possível marcar a leitura.");
        }
        const dados = await resposta.json();
        if (!dados.lida) {
            throw new Error("A leitura não foi confirmada.");
        }
        resultado = dados;
    } catch {
        avisosSistema.mostrar("Não foi possível marcar como lida. Tente novamente.", "error");
    } finally {
        leituraEmAndamento = false;
        botoes.forEach((controle) => { controle.disabled = false; });
    }

    if (!resultado) {
        botao.focus({ preventScroll: true });
        return;
    }

    botaoTodas.disabled = !resultado.tem_nao_lidas;
    registrarMudancaNotificacoes(resultado);
    if (todas) {
        painelNotificacoes.querySelectorAll(".notificacao-nova").forEach(marcarItemLido);
        document.querySelector("#titulo-pagina").focus({ preventScroll: true });
    } else {
        marcarItemLido(item).focus({ preventScroll: true });
    }
    avisosSistema.mostrar(todas
        ? "Todas as notificações foram marcadas como lidas."
        : "Notificação marcada como lida.", "success");
});

document.addEventListener("notificacoes:sincronizar", async (event) => {
    listaPendente ||= event.detail;
    if (!listaPendente || leituraEmAndamento || consultaLista) return;

    const controle = new AbortController();
    consultaLista = controle;
    listaPendente = false;
    const url = new URL(window.location.href);
    url.searchParams.set("fragmento", "lista");

    try {
        const resposta = await fetch(url, { cache: "no-store", signal: controle.signal });
        if (!resposta.ok || resposta.redirected) throw new Error("Lista indisponível.");
        const pagina = new DOMParser().parseFromString(await resposta.text(), "text/html");
        controle.signal.throwIfAborted();
        const novaLista = pagina.querySelector(".notificacoes-card");
        if (!novaLista) throw new Error("Lista ausente na resposta.");

        const foco = document.activeElement;
        const formulario = foco.closest("form");
        const destino = foco.closest("a")?.getAttribute("href");
        const manterFoco = painelNotificacoes.contains(foco);
        painelNotificacoes.replaceChildren(...novaLista.childNodes);
        if (manterFoco) {
            const controleFocado = Array.from(painelNotificacoes.querySelectorAll("a[href], form button:enabled"))
                .find((item) => formulario
                    ? item.closest("form")?.action === formulario.action
                    : destino && item.getAttribute("href") === destino);
            (controleFocado || document.querySelector("#titulo-pagina")).focus({ preventScroll: true });
        }
    } catch {
        listaPendente = true;
    } finally {
        consultaLista = null;
    }
});
