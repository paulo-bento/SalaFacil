const formulario = document.querySelector("#reserva-form");
const mensagem = document.querySelector("#reserva-feedback");
const consultar = document.querySelector("#reserva-consultar");
const botao = document.querySelector("#reserva-submit");

if (formulario) {
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

        mensagem.hidden = true;
        consultar.hidden = true;
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

            mensagem.textContent = resposta.ok
                ? resultado.mensagem
                : resultado.erro || "Não foi possível criar a reserva.";

            mensagem.dataset.status = resposta.ok
                ? "success"
                : "error";

            mensagem.hidden = false;

            if (resposta.ok) {
                consultar.href =
                    `/?data=${encodeURIComponent(dados.data)}`;

                consultar.hidden = false;
            }
        } catch (erro) {
            mensagem.textContent =
                "Não foi possível comunicar com o servidor.";

            mensagem.dataset.status = "error";
            mensagem.hidden = false;
        } finally {
            botao.disabled = false;
        }
    });
}
