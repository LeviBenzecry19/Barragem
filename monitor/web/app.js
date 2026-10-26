// Dashboard do monitor de barragem. Atualiza a cada INTERVALO_MS.
"use strict";

const INTERVALO_MS = 5000;
const CORES = { Normal: "#2e9d5b", "Atenção": "#d9a400", Alerta: "#e46b12", "Crítico": "#cf2e2e" };
const ROTULOS_DERIVADOS = {
  pressao_hidrostatica_base_kpa: ["Pressão hidrostática na base", "kPa"],
  carga_piezometrica_m: ["Carga piezométrica", "m"],
  tensao_total_kpa: ["Tensão total (σ)", "kPa"],
  tensao_efetiva_kpa: ["Tensão efetiva (σ')", "kPa"],
  razao_poropressao_ru: ["Razão de poropressão (rᵤ)", ""],
  chuva_antecedente_mm: ["Chuva antecedente (API)", "mm"],
};

let sensores = [];
let modos = [];
let variavelSelecionada = "pressao_poros";
let graficoVariavel = null;
let graficoIndice = null;

const $ = (id) => document.getElementById(id);
const fmt = (v, casas = 2) =>
  v === null || v === undefined
    ? "—"
    : Number(v).toLocaleString("pt-BR", { maximumFractionDigits: Math.abs(v) < 1 && v !== 0 ? Math.max(casas, 3) : casas });
function nomeOrigem(origem) {
  if (origem.startsWith("modo:")) {
    const m = modos.find((x) => `modo:${x.chave}` === origem);
    return m ? `Modo: ${m.nome}` : "Modo de ruptura";
  }
  return (sensores.find((s) => s.variavel === origem) || { nome: "Nível global" }).nome;
}
const hora = (iso) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

function selo(nivel) {
  return `<span class="selo n-${nivel}">${nivel}</span>`;
}

async function obter(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

// ---------------------------------------------------------------------------

function renderEstado(estado) {
  sensores = estado.sensores;
  const av = estado.avaliacao;
  const global = $("nivel-global");

  if (!av) {
    global.textContent = "Sem dados";
    $("sensores").innerHTML = '<p class="cartao">Aguardando leituras. Rode o simulador ou conecte a estação.</p>';
    return;
  }

  $("atualizado").textContent = hora(av.instante);
  global.textContent = av.nivel;
  global.className = `selo selo-grande n-${av.nivel}`;

  $("indice").innerHTML = `${fmt(av.indice, 3)} ${selo(av.nivel_indice)}`;
  $("indice-marcador").style.left = `${Math.min(av.indice, 1) * 100}%`;
  $("cobertura").textContent = `Cobertura dos sensores do índice: ${fmt(av.cobertura * 100, 0)}%`;
  $("fs").textContent = fmt(av.fator_seguranca, 2);

  $("derivados").innerHTML = Object.entries(av.derivados)
    .map(([k, v]) => {
      const [rotulo, un] = ROTULOS_DERIVADOS[k] || [k, ""];
      return `<dt>${rotulo}</dt><dd>${fmt(v, 2)} ${un}</dd>`;
    })
    .join("");
  $("motivos").innerHTML = av.motivos.map((m) => `<li>${escapar(m)}</li>`).join("");
  renderModos(av);

  $("sensores").innerHTML = sensores
    .map((s) => {
      const d = av.variaveis[s.variavel];
      const leitura = estado.leituras[s.variavel];
      const nivel = d ? d.nivel : null;
      return `
        <article class="cartao sensor ${s.variavel === variavelSelecionada ? "selecionado" : ""}"
                 data-variavel="${s.variavel}" tabindex="0">
          <h2>${s.nome}</h2>
          <div class="linha">
            <span><span class="valor">${fmt(d && d.valor)}</span> <span class="unidade">${s.unidade}</span></span>
            ${nivel ? selo(nivel) : '<span class="selo">sem leitura</span>'}
          </div>
          <div class="limites">${s.equipamento} · limites A/Al/C: ${fmt(s.atencao)} / ${fmt(s.alerta)} / ${fmt(s.critico)}</div>
          <div class="peso">${s.peso > 0 ? `Peso no índice: ${fmt(s.peso * 100, 0)}%` : "Fora do índice (alerta individual)"}
            ${leitura ? ` · ${leitura.estacao}` : ""}</div>
        </article>`;
    })
    .join("");

  document.querySelectorAll(".sensor").forEach((el) => {
    const escolher = () => {
      variavelSelecionada = el.dataset.variavel;
      $("sel-variavel").value = variavelSelecionada;
      document.querySelectorAll(".sensor").forEach((c) => c.classList.toggle("selecionado", c === el));
      atualizarGraficos();
    };
    el.addEventListener("click", escolher);
    el.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && escolher());
  });

  const sel = $("sel-variavel");
  if (!sel.options.length) {
    sel.innerHTML = sensores.map((s) => `<option value="${s.variavel}">${s.nome}</option>`).join("");
    sel.value = variavelSelecionada;
  }
  $("pendentes").textContent = estado.alertas_pendentes ? `(${estado.alertas_pendentes} pendentes)` : "";
}

function valorIndicador(i) {
  if (i.valor === null) return "";
  const n = Number(i.valor).toLocaleString("pt-BR", { minimumFractionDigits: i.casas, maximumFractionDigits: i.casas });
  return `${n}${i.unidade ? " " + i.unidade : ""}`;
}

function renderModos(av) {
  const el = $("modos");
  if (!av.modos) {
    el.innerHTML = '<p class="cartao detalhe">A última avaliação é anterior à análise por modos de ruptura. Envie uma nova leitura.</p>';
    return;
  }
  modos = av.modos;
  el.innerHTML = modos
    .map((m) => {
      const lista = m.indicadores.length
        ? `<ul class="indicadores">${m.indicadores
            .map(
              (i) => `
          <li class="${i.nivel ? "" : "informativo"}">
            <div class="ind-linha"><span>${escapar(i.nome)}</span>
              <span class="ind-valor">${valorIndicador(i)}${i.nivel ? " " + selo(i.nivel) : ""}</span></div>
            ${i.detalhe ? `<div class="ind-detalhe">${escapar(i.detalhe)}</div>` : ""}
          </li>`
            )
            .join("")}</ul>`
        : '<p class="detalhe">Faltam leituras ou histórico para avaliar este modo.</p>';
      return `
        <article class="cartao modo">
          <div class="modo-topo"><h2>${escapar(m.nome)}</h2>${m.nivel ? selo(m.nivel) : '<span class="selo">sem dados</span>'}</div>
          ${lista}
        </article>`;
    })
    .join("");
}

function renderAlertas(alertas) {
  const corpo = $("alertas");
  if (!alertas.length) {
    corpo.innerHTML = '<tr><td colspan="5">Nenhum alerta.</td></tr>';
    return;
  }
  corpo.innerHTML = alertas
    .map(
      (a) => `
      <tr class="${a.reconhecido ? "reconhecido" : ""}">
        <td>${hora(a.instante)}</td>
        <td>${escapar(nomeOrigem(a.origem))}</td>
        <td>${selo(a.nivel)}</td>
        <td>${escapar(a.mensagem)}</td>
        <td>${a.reconhecido ? "✓" : `<button data-id="${a.id}">Reconhecer</button>`}</td>
      </tr>`
    )
    .join("");
  corpo.querySelectorAll("button[data-id]").forEach((b) =>
    b.addEventListener("click", async () => {
      await fetch(`/api/alertas/${b.dataset.id}/reconhecer`, { method: "POST" });
      atualizar();
    })
  );
}

// ---------------------------------------------------------------------------

function linhaLimite(rotulo, valor, cor, n) {
  return {
    label: rotulo, data: Array(n).fill(valor), borderColor: cor, borderDash: [6, 4],
    borderWidth: 1, pointRadius: 0, fill: false,
  };
}

function desenhar(grafico, canvas, labels, datasets, opcoesY = {}) {
  if (typeof Chart === "undefined") {
    canvas.parentElement.innerHTML = '<p class="detalhe">Gráficos indisponíveis (Chart.js não carregou — sem internet?).</p>';
    return null;
  }
  if (grafico) {
    grafico.data.labels = labels;
    grafico.data.datasets = datasets;
    Object.assign(grafico.options.scales.y, opcoesY);
    grafico.update("none");
    return grafico;
  }
  Chart.defaults.color = getComputedStyle(document.body).getPropertyValue("--suave").trim() || "#5c6b7a";
  return new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      scales: { x: { ticks: { maxTicksLimit: 8, autoSkip: true } }, y: { ...opcoesY } },
      plugins: { legend: { labels: { boxWidth: 12 } } },
    },
  });
}

async function atualizarGraficos() {
  const horas = $("sel-horas").value;
  const s = sensores.find((x) => x.variavel === variavelSelecionada);
  if (!s) return;

  const [hist, ind] = await Promise.all([
    obter(`/api/historico?variavel=${variavelSelecionada}&horas=${horas}`),
    obter(`/api/indice?horas=${horas}`),
  ]);

  $("titulo-grafico").textContent = `${s.nome} (${s.unidade})`;
  const labels = hist.pontos.map((p) => hora(p.instante));
  const n = labels.length;
  graficoVariavel = desenhar(graficoVariavel, $("grafico-variavel"), labels, [
    { label: s.nome, data: hist.pontos.map((p) => p.valor), borderColor: "#1f6fb2", borderWidth: 2, pointRadius: 0, tension: 0.2 },
    linhaLimite("Atenção", s.atencao, CORES["Atenção"], n),
    linhaLimite("Alerta", s.alerta, CORES.Alerta, n),
    linhaLimite("Crítico", s.critico, CORES["Crítico"], n),
  ]);

  const li = ind.pontos.map((p) => hora(p.instante));
  graficoIndice = desenhar(graficoIndice, $("grafico-indice"), li, [
    { label: "Índice", data: ind.pontos.map((p) => p.indice), borderColor: "#6b4fbb", borderWidth: 2, pointRadius: 0, tension: 0.2 },
    linhaLimite("Atenção", 0.25, CORES["Atenção"], li.length),
    linhaLimite("Alerta", 0.5, CORES.Alerta, li.length),
    linhaLimite("Crítico", 0.75, CORES["Crítico"], li.length),
  ], { min: 0, max: 1 });
}

async function atualizar() {
  try {
    const [estado, alertas] = await Promise.all([obter("/api/estado"), obter("/api/alertas")]);
    renderEstado(estado);
    renderAlertas(alertas.alertas);
    if (estado.avaliacao) await atualizarGraficos();
  } catch (e) {
    console.error(e);
    $("atualizado").textContent = "erro de conexão com o servidor";
  }
}

$("sel-variavel").addEventListener("change", (e) => {
  variavelSelecionada = e.target.value;
  atualizar();
});
$("sel-horas").addEventListener("change", atualizarGraficos);

atualizar();
setInterval(atualizar, INTERVALO_MS);
