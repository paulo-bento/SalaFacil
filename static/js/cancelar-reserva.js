const dialogoCancelamento = document.querySelector("#cancelamento-reserva");
const formularioCancelamento = document.querySelector("#cancelamento-form");
const manterReserva = document.querySelector("#manter-reserva");
const confirmarCancelamento = document.querySelector("#confirmar-cancelamento");
let botaoReserva;

document.querySelectorAll(".btn-cancelar-reserva").forEach((botao) => {
    botao.addEventListener("click", () => {
        botaoReserva = botao;
        const { sala, data, horario } = botao.dataset;
        document.querySelector("#cancelamento-sala").textContent = sala;
        document.querySelector("#cancelamento-data").textContent = data;
        document.querySelector("#cancelamento-horario").textContent = horario;
        dialogoCancelamento.showModal();
    });
});

manterReserva.addEventListener("click", () => dialogoCancelamento.close());

dialogoCancelamento.addEventListener("cancel", (event) => {
    if (confirmarCancelamento.disabled) {
        event.preventDefault();
    }
});

dialogoCancelamento.addEventListener("close", () => {
    botaoReserva.focus({ preventScroll: true });
});

formularioCancelamento.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (confirmarCancelamento.disabled) {
        return;
    }

    manterReserva.disabled = true;
    confirmarCancelamento.disabled = true;
    confirmarCancelamento.textContent = "Cancelando…";

    try {
        const resposta = await fetch(botaoReserva.dataset.cancelarUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": formularioCancelamento.elements.csrfmiddlewaretoken.value,
            },
            credentials: "same-origin",
        });
        const dados = await resposta.json().catch(() => ({}));
        if (!resposta.ok || dados.status !== "cancelada") {
            throw new Error(dados.erro || "Não foi possível cancelar a reserva. Tente novamente.");
        }

        const status = botaoReserva.closest("tr").querySelector(".reserva-status");
        status.textContent = dados.status_label;
        status.classList.replace("reserva-status--confirmada", "reserva-status--cancelada");

        const semAcao = document.createElement("span");
        semAcao.textContent = "—";
        botaoReserva.replaceWith(semAcao);

        dialogoCancelamento.close();
        registrarMudancaNotificacoes(dados);
        avisosSistema.mostrar(dados.mensagem, "success");
        status.tabIndex = -1;
        status.focus({ preventScroll: true });
    } catch (erro) {
        const mensagem = erro instanceof TypeError
            ? "Não foi possível comunicar com o servidor. Tente novamente."
            : erro.message;
        avisosSistema.mostrar(mensagem, "error");
    } finally {
        manterReserva.disabled = false;
        confirmarCancelamento.disabled = false;
        confirmarCancelamento.textContent = "Confirmar cancelamento";
        if (dialogoCancelamento.open) {
            confirmarCancelamento.focus();
        }
    }
});
