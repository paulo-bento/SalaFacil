const navegacaoDashboard = document.querySelector("#navegacao-dashboard");
const telaAtual = window.location.pathname;
const prefixoRolagem = `salafacil:rolagem:${navegacaoDashboard.dataset.usuario}:`;
const chaveDestino = `${prefixoRolagem}destino`;

navegacaoDashboard.addEventListener("click", (event) => {
    const link = event.target.closest("a.nav-item");
    if (!link || link.pathname === telaAtual || event.defaultPrevented ||
        event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
        return;
    }

    try {
        sessionStorage.setItem(`${prefixoRolagem}${telaAtual}`, String(window.scrollY));
        sessionStorage.setItem(chaveDestino, link.pathname);
    } catch {
        // A troca de tela funciona mesmo quando o navegador bloqueia o armazenamento.
    }
});

window.addEventListener("pageshow", (event) => {
    try {
        const destino = sessionStorage.getItem(chaveDestino);
        sessionStorage.removeItem(chaveDestino);
        const navegacao = performance.getEntriesByType("navigation")[0];
        if (destino !== telaAtual || event.persisted || navegacao?.type !== "navigate") {
            return;
        }

        const posicao = sessionStorage.getItem(`${prefixoRolagem}${telaAtual}`);
        if (posicao !== null) {
            window.scrollTo({ top: Number(posicao), behavior: "instant" });
        }
    } catch {
        // Sem acesso ao armazenamento, o navegador mantém sua rolagem padrão.
    }
});
