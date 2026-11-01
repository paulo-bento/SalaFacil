
document.addEventListener("DOMContentLoaded", () => {
    const dialogo = document.querySelector("#reserva-detalhes");
    const fechar = document.querySelector("#fechar-detalhes");
    const finalidadeContainer = document.querySelector(
        "#detalhes-finalidade-container"
    );

    if (!dialogo) {
        return;
    }

    document.querySelectorAll(".slot-details").forEach((botao) => {
        botao.addEventListener("click", () => {
            const dados = botao.dataset;

            document.querySelector("#detalhes-sala").textContent =
                dados.sala;
            document.querySelector("#detalhes-data").textContent =
                dados.data;
            document.querySelector("#detalhes-horario").textContent =
                `${dados.inicio} às ${dados.fim}`;
            document.querySelector("#detalhes-status").textContent =
                dados.status;

            const temFinalidade = dados.finalidade !== undefined;

            finalidadeContainer.hidden = !temFinalidade;

            document.querySelector("#detalhes-finalidade").textContent =
                temFinalidade ? dados.finalidade : "";

            dialogo.showModal();
        });
    });

    fechar.addEventListener("click", () => {
        dialogo.close();
    });
});
