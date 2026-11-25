
document.addEventListener("DOMContentLoaded", () => {
    const dialogo = document.querySelector("#reserva-detalhes");
    const finalidadeContainer = document.querySelector(
        "#detalhes-finalidade-container"
    );

    if (!dialogo) {
        return;
    }

    document.querySelector("#app-content").addEventListener("click", (event) => {
        const botao = event.target.closest(".slot-details");
        if (!botao) {
            return;
        }

        const dados = botao.dataset;
        document.querySelector("#detalhes-sala").textContent = dados.sala;
        document.querySelector("#detalhes-data").textContent = dados.data;
        document.querySelector("#detalhes-horario").textContent =
            `${dados.inicio} às ${dados.fim}`;
        document.querySelector("#detalhes-status").textContent = dados.status;
        document.querySelector("#detalhes-responsavel").textContent = dados.responsavel;

        const temFinalidade = dados.finalidade !== undefined;

        finalidadeContainer.hidden = !temFinalidade;

        document.querySelector("#detalhes-finalidade").textContent =
            temFinalidade ? dados.finalidade : "";

        dialogo.showModal();
    });
});
