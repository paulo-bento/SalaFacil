window.avisosSistema = (() => {
    const painel = document.querySelector("#avisos-sistema");
    const aviso = painel.querySelector("[data-aviso-ativo]");
    const texto = painel.querySelector("[data-aviso-texto]");
    const botao = painel.querySelector("[data-aviso-fechar]");
    const status = painel.querySelector("[data-aviso-status]");
    const alerta = painel.querySelector("[data-aviso-alerta]");
    const temPonteiroComHover = matchMedia("(any-hover: hover)");
    const fila = [];
    let atual;
    let tempoRestante;
    let iniciadoEm;
    let temporizador;
    let focoAnterior;

    function atualizarTempo() {
        if (temporizador !== undefined) {
            clearTimeout(temporizador);
            temporizador = undefined;
            tempoRestante -= performance.now() - iniciadoEm;
        }
        const sobPonteiro = temPonteiroComHover.matches && aviso.matches(":hover");
        if (atual && !document.hidden && !sobPonteiro && !aviso.matches(":focus-within")) {
            iniciadoEm = performance.now();
            temporizador = setTimeout(fechar, Math.max(0, tempoRestante));
        }
    }

    function posicionar() {
        const destino = document.querySelector("dialog:modal") || document.body;
        if (painel.parentElement !== destino) {
            destino.append(painel);
        }
    }

    function mostrarProximo() {
        atual = fila.shift();
        if (!atual) return;
        posicionar();
        aviso.dataset.tipo = atual.tipo;
        texto.textContent = atual.mensagem;
        aviso.hidden = false;
        const urgente = atual.tipo === "error" || atual.tipo === "warning";
        (urgente ? alerta : status).textContent = atual.mensagem;
        tempoRestante = urgente ? 8000 : 5000;
        atualizarTempo();
    }

    function fechar() {
        clearTimeout(temporizador);
        temporizador = undefined;
        const restaurarFoco = aviso.contains(document.activeElement);
        if (restaurarFoco) {
            botao.blur();
            if (focoAnterior?.isConnected) focoAnterior.focus({ preventScroll: true });
        }
        aviso.hidden = true;
        status.textContent = "";
        alerta.textContent = "";
        mostrarProximo();
    }

    function mostrar(mensagem, tipo = "info", origem = "") {
        if (!mensagem) return;
        const repetido = (item) => item?.mensagem === mensagem && item.tipo === tipo && item.origem === origem;
        if (repetido(atual) || fila.some(repetido)) return;
        fila.push({ mensagem, tipo, origem });
        if (!atual) mostrarProximo();
    }

    function remover(origem) {
        for (let indice = fila.length - 1; indice >= 0; indice--) {
            if (fila[indice].origem === origem) fila.splice(indice, 1);
        }
        if (atual?.origem === origem) fechar();
    }

    botao.addEventListener("click", fechar);
    aviso.addEventListener("pointerenter", atualizarTempo);
    aviso.addEventListener("pointerleave", atualizarTempo);
    aviso.addEventListener("focusin", (event) => {
        focoAnterior = event.relatedTarget;
        atualizarTempo();
    });
    aviso.addEventListener("focusout", () => queueMicrotask(atualizarTempo));
    document.addEventListener("visibilitychange", atualizarTempo);

    const observarDialogos = new MutationObserver(() => {
        posicionar();
        atualizarTempo();
    });
    document.querySelectorAll("dialog").forEach((dialogo) => {
        observarDialogos.observe(dialogo, { attributeFilter: ["open"] });
    });

    painel.querySelectorAll("[data-aviso-inicial]").forEach((inicial) => {
        mostrar(inicial.textContent, inicial.dataset.avisoInicial);
        inicial.remove();
    });
    return { mostrar, remover };
})();
