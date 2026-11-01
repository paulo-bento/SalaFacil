
document.addEventListener("DOMContentLoaded", () => {
    const botoes = document.querySelectorAll(".btn-cancelar-reserva");

    botoes.forEach((botao) => {
        botao.addEventListener("click", async () => {
            const reservaId = botao.dataset.reservaId;

            if (!confirm("Deseja realmente cancelar esta reserva?")) {
                return;
            }

            botao.disabled = true;

            try {
                const resposta = await fetch(
                    `/bookings/cancelar/${reservaId}/`,
                    {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": document.cookie
                                .split("; ")
                                .find((item) => item.startsWith("csrftoken="))
                                ?.split("=")[1] || "",
                        },
                        credentials: "same-origin",
                    }
                );

                const dados = await resposta.json();

                if (!resposta.ok) {
                    throw new Error(dados.erro || "Erro ao cancelar reserva.");
                }

                window.location.reload();
            } catch (erro) {
                alert(erro.message);
                botao.disabled = false;
            }
        });
    });
});
