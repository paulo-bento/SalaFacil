const formulario = document.querySelector("#reserva-form");
const botao = document.querySelector("#reserva-submit");
let campoReservaInvalido;

function limparErroCampoReserva() {
    if (!campoReservaInvalido) return;
    formulario.querySelector("#reserva-erro-campo")?.remove();
    campoReservaInvalido.removeAttribute("aria-invalid");
    campoReservaInvalido.removeAttribute("aria-describedby");
    campoReservaInvalido = null;
}

if (formulario) {
    formulario.addEventListener("input", limparErroCampoReserva);
    formulario.addEventListener("submit", async (event) => {
        event.preventDefault();

        const campos = formulario.elements;

        const dados = {
            sala_id: Number(campos.sala_id.value),
            data: campos.data.value,
            inicio: campos.inicio.value,
            fim: campos.fim.value,
            finalidade: campos.finalidade.value.trim(),
        };

        limparErroCampoReserva();
        botao.disabled = true;

        try {
            const resposta = await fetch(formulario.action, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": campos.csrfmiddlewaretoken.value,
                },
                credentials: "same-origin",
                body: JSON.stringify(dados),
            });

            const resultado = await resposta.json();

            if (!resposta.ok) {
                const mensagem = resultado.erro || "Não foi possível criar a reserva.";
                if (resultado.campo) {
                    campoReservaInvalido = campos.namedItem(resultado.campo);
                }
                if (campoReservaInvalido) {
                    const descricao = document.createElement("span");
                    descricao.id = "reserva-erro-campo";
                    descricao.className = "reserva-erro-campo";
                    descricao.textContent = mensagem;
                    campoReservaInvalido.after(descricao);
                    campoReservaInvalido.setAttribute("aria-invalid", "true");
                    campoReservaInvalido.setAttribute("aria-describedby", descricao.id);
                }
                avisosSistema.mostrar(mensagem, "error");
                return;
            }

            registrarMudancaNotificacoes(resultado);
            const url = new URL(window.location.href);
            url.searchParams.set("data", dados.data);
            try {
                await atualizarAgenda(url, { ancora: formulario, historico: "replaceState" });
            } catch (erro) {
                if (erro.name !== "AbortError") {
                    avisosSistema.mostrar(
                        "Reserva confirmada. Para atualizar a agenda, selecione a data da reserva e clique em Consultar.",
                        "warning",
                    );
                    return;
                }
            }
            avisosSistema.mostrar(resultado.mensagem, "success");
        } catch {
            avisosSistema.mostrar("Não foi possível comunicar com o servidor.", "error");
        } finally {
            botao.disabled = false;
        }
    });
}
