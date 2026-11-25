const formularioPreferencia = document.querySelector("#notificacoes-preferencia-form");
const botaoPreferencia = formularioPreferencia.elements.receber;

function atualizarInterruptorNotificacoes(ativos) {
    botaoPreferencia.setAttribute("aria-checked", String(ativos));
    botaoPreferencia.value = ativos ? "0" : "1";
    botaoPreferencia.querySelector("[data-preferencia-rotulo]").textContent = ativos ? "Ativados" : "Desativados";
}

formularioPreferencia.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (botaoPreferencia.getAttribute("aria-disabled") === "true") return;

    const dados = new FormData(formularioPreferencia, botaoPreferencia);
    botaoPreferencia.setAttribute("aria-disabled", "true");

    try {
        const resposta = await fetch(formularioPreferencia.action, {
            method: "POST",
            headers: { Accept: "application/json" },
            body: dados,
            credentials: "same-origin",
        });
        if (!resposta.ok || resposta.redirected) throw new Error("Preferência indisponível.");

        const estado = await resposta.json();
        if (typeof estado.avisos_notificacoes_ativos !== "boolean") {
            throw new Error("Preferência não confirmada.");
        }

        registrarMudancaNotificacoes(estado);
        atualizarInterruptorNotificacoes(avisosNotificacoesAtivos);
        avisosSistema.mostrar("Preferência salva.", "success");
    } catch {
        avisosSistema.mostrar("Não foi possível salvar a preferência. Tente novamente.", "error");
    } finally {
        botaoPreferencia.removeAttribute("aria-disabled");
    }
});

document.addEventListener("notificacoes:sincronizar", () => {
    if (botaoPreferencia.getAttribute("aria-disabled") !== "true") {
        atualizarInterruptorNotificacoes(avisosNotificacoesAtivos);
    }
});
