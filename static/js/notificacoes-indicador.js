const painelEstadoNotificacoes = document.querySelector("#estado-notificacoes");
let totalNotificacoes = Number(painelEstadoNotificacoes.dataset.total);
let ultimaNotificacao = Number(painelEstadoNotificacoes.dataset.ultimaId);
let avisosNotificacoesAtivos = painelEstadoNotificacoes.dataset.avisosAtivos === "true";
let consultaNotificacoes;
const canalNotificacoes = typeof BroadcastChannel === "function"
    ? new BroadcastChannel(`salafacil:notificacoes:${painelEstadoNotificacoes.dataset.usuario}`)
    : null;

function atualizarContadorNotificacoes(total) {
    if (!Number.isInteger(total) || total < 0) {
        return;
    }

    document.querySelectorAll("[data-link-notificacoes]").forEach((link) => {
        const contador = link.querySelector("[data-contador-notificacoes]");
        contador.textContent = total > 99 ? "99+" : String(total);
        contador.hidden = total === 0;
        link.setAttribute("aria-label", total === 0
            ? "Notificações"
            : `Notificações: ${total} ${total === 1 ? "não lida" : "não lidas"}`);
    });
}

function aplicarEstadoNotificacoes(estado) {
    totalNotificacoes = estado.notificacoes_nao_lidas;
    ultimaNotificacao = estado.ultima_notificacao_id;
    avisosNotificacoesAtivos = estado.avisos_notificacoes_ativos;
    atualizarContadorNotificacoes(avisosNotificacoesAtivos ? totalNotificacoes : 0);
    if (!avisosNotificacoesAtivos) {
        avisosSistema.remover("notificacao");
    }
}

function registrarMudancaNotificacoes(estado) {
    consultaNotificacoes?.abort();
    aplicarEstadoNotificacoes(estado);
    canalNotificacoes?.postMessage("atualizar");
}

function notificacoesMudaram(estado) {
    return estado.notificacoes_nao_lidas !== totalNotificacoes ||
        estado.ultima_notificacao_id !== ultimaNotificacao;
}

async function sincronizarNotificacoes() {
    consultaNotificacoes?.abort();
    const controle = new AbortController();
    consultaNotificacoes = controle;

    try {
        const resposta = await fetch(painelEstadoNotificacoes.dataset.urlEstado, {
            cache: "no-store",
            signal: controle.signal,
        });
        if (!resposta.ok || resposta.redirected) {
            return;
        }

        const estado = await resposta.json();
        controle.signal.throwIfAborted();
        const mudou = notificacoesMudaram(estado);
        const recebeu = avisosNotificacoesAtivos && (
            estado.ultima_notificacao_id > ultimaNotificacao ||
            estado.notificacoes_nao_lidas > totalNotificacoes
        );

        aplicarEstadoNotificacoes(estado);
        if (recebeu && avisosNotificacoesAtivos && totalNotificacoes > 0 && !document.hidden) {
            avisosSistema.mostrar("Você tem uma nova notificação.", "info", "notificacao");
        }
        document.dispatchEvent(new CustomEvent("notificacoes:sincronizar", { detail: mudou }));
    } catch {
        // Uma falha de rede não deve interromper a próxima consulta.
    } finally {
        if (consultaNotificacoes === controle) {
            consultaNotificacoes = null;
        }
    }
}

canalNotificacoes?.addEventListener("message", sincronizarNotificacoes);
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) sincronizarNotificacoes();
});
window.addEventListener("pageshow", (event) => {
    if (event.persisted) sincronizarNotificacoes();
});
setInterval(() => {
    if (!document.hidden && !consultaNotificacoes) sincronizarNotificacoes();
}, 10000);
