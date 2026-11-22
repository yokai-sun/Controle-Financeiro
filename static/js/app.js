// ================= utilidades =================
const $ = (sel) => document.querySelector(sel);
const fmtBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const brl = (v) => fmtBRL.format(Number(v) || 0);

// ---- campos de dinheiro: "R$ 1.500,00" enquanto digita ----
const fmtNum = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const moedaParaTexto = (v) => (v === "" || v === null || v === undefined ? "" : fmtNum.format(Number(v) || 0));
const lerMoeda = (s) => {
  const t = String(s ?? "").trim();
  return t ? Number(t.replace(/\./g, "").replace(",", ".")) || 0 : "";
};
function htmlMoeda({ nome = "", id = "", classe = "", valor = "", obrigatorio = false, placeholder = "0,00" } = {}) {
  return `<div class="campo-afixo"><span class="afixo">R$</span><input type="text" inputmode="numeric" autocomplete="off"
    class="moeda ${classe}" ${nome ? `name="${nome}"` : ""} ${id ? `id="${id}"` : ""} value="${esc(moedaParaTexto(valor))}"
    placeholder="${esc(placeholder)}" ${obrigatorio ? "required" : ""}></div>`;
}
document.addEventListener("input", (e) => {
  if (!e.target.classList?.contains("moeda")) return;
  const digitos = e.target.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 13);
  e.target.value = digitos ? fmtNum.format(Number(digitos) / 100) : "";
}, true); // captura: formata antes de qualquer outro listener ler o valor
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const nomeMes = (m) => (m ? `${MESES[Number(m.slice(5, 7)) - 1]}/${m.slice(0, 4)}` : "—");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const hojeISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
// Ícones SVG do sprite em index.html (decorativos: escondidos de leitores de tela)
const ic = (nome, cls = "") => `<svg class="ic ${cls}" aria-hidden="true"><use href="#i-${nome}"/></svg>`;
// Objetivos guardam um emoji no banco; na tela mostramos o ícone SVG equivalente
const ICONES_OBJETIVO = {
  "🎯": ["alvo", "Meta"], "✈️": ["aviao", "Viagem"], "🎓": ["estudo", "Estudos / intercâmbio"], "🚗": ["carro", "Carro"],
  "🏠": ["casa", "Casa"], "💍": ["joia", "Casamento"], "💻": ["notebook", "Eletrônicos"], "🏖️": ["praia", "Férias"],
  "🛡️": ["escudo", "Reserva de emergência"], "👶": ["bebe", "Filhos"],
};
const iconeObjetivo = (e) => (ICONES_OBJETIVO[e] ? ic(ICONES_OBJETIVO[e][0]) : esc(e || ""));
const aviso = (tipo, icone, html) => `<div class="aviso ${tipo}" role="status">${ic(icone)}<div>${html}</div></div>`;
// Cores das categorias: as cores padrão viram a paleta validada (skill dataviz), em ordem fixa
// e ajustada ao tema. Cores escolhidas pelo usuário são mantidas como estão.
const SERIE_POR_COR_PADRAO = {
  "#6366f1": 1, "#f59e0b": 2, "#0ea5e9": 3, "#f97316": 4, "#ec4899": 5,
  "#10b981": 6, "#8b5cf6": 7, "#ef4444": 8, "#64748b": "neutra", "#94a3b8": "neutra",
};
const corCategoria = (cor) => {
  const s = SERIE_POR_COR_PADRAO[String(cor || "#94a3b8").toLowerCase()];
  return s ? corCSS(`--serie-${s}`) : cor;
};
const dataBR = (iso) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const meses = (n) => (n === null || n === undefined ? "—" : n === 1 ? "1 mês" : `${n} meses`);
const tempoLegivel = (n) => {
  if (n === null || n === undefined) return "sem previsão";
  if (n === 0) return "já conseguiu!";
  const a = Math.floor(n / 12), m = n % 12;
  const partes = [];
  if (a) partes.push(a === 1 ? "1 ano" : `${a} anos`);
  if (m) partes.push(m === 1 ? "1 mês" : `${m} meses`);
  return partes.join(" e ");
};

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("visivel");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove("visivel"), 2600);
}

function deslocarMes(mes, n) {
  const [a, m] = mes.split("-").map(Number);
  const total = a * 12 + (m - 1) + n;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, "0")}`;
}

// ================= estado =================
const estado = {
  mes: hojeISO().slice(0, 7),
  aba: "painel",
  categorias: [],
  graficos: {},
};
const TITULOS = {
  painel: "Painel", fixos: "Renda, contas e parcelas", lancamentos: "Lançamentos",
  objetivos: "Objetivos", simulador: "Simulador de metas", dicas: "Onde posso economizar",
};
const catPorId = (id) => estado.categorias.find((c) => c.id === id);
const opcoesCategorias = () => [{ valor: "", texto: "Sem categoria" }, ...estado.categorias.map((c) => ({ valor: c.id, texto: c.nome }))];

// ================= modal de formulário genérico =================
function abrirFormulario({ titulo, campos, valores = {}, aoSalvar, preview }) {
  const modal = $("#modal");
  $("#modal-titulo").textContent = titulo;
  $("#modal-erro").textContent = "";
  const cont = $("#modal-campos");
  cont.innerHTML = "";
  for (const c of campos) {
    const v = valores[c.nome] ?? c.padrao ?? "";
    let html;
    if (c.tipo === "select") {
      html = `<label>${esc(c.label)}<select name="${c.nome}">${c.opcoes
        .map((o) => `<option value="${esc(o.valor)}" ${String(o.valor) === String(v) ? "selected" : ""}>${esc(o.texto)}</option>`)
        .join("")}</select></label>`;
    } else if (c.tipo === "checkbox") {
      html = `<label class="check"><input type="checkbox" name="${c.nome}" ${v ? "checked" : ""}> ${esc(c.label)}</label>`;
    } else if (c.tipo === "moeda") {
      html = `<label>${esc(c.label)}${htmlMoeda({ nome: c.nome, valor: v, obrigatorio: c.obrigatorio, placeholder: c.placeholder || "0,00" })}</label>`;
    } else if (c.tipo === "inteiro") {
      const input = `<input type="number" name="${c.nome}" value="${esc(v)}" min="${c.min ?? 1}" ${c.max ? `max="${c.max}"` : ""}
        step="1" ${c.obrigatorio ? "required" : ""} placeholder="${esc(c.placeholder || "")}">`;
      html = `<label>${esc(c.label)}${c.sufixo
        ? `<div class="campo-afixo sufixo">${input}<span class="afixo">${esc(c.sufixo)}</span></div>` : input}</label>`;
    } else if (c.tipo === "pagamento") {
      // linha de parcela: [x] Parcela 3 · jan/2027 (vence 10/01)   [data do pagamento]
      const pv = v || {};
      html = `<div class="pag-linha ${pv.atrasada ? "atrasada" : ""}">
        <label class="check"><input type="checkbox" name="${c.nome}" ${pv.pago ? "checked" : ""} data-data-padrao="${esc(c.dataPadrao || "")}">
          <span>${esc(c.label)}<small>${esc(c.detalhe || "")}</small></span></label>
        <input type="date" name="${c.nome}_data" value="${esc(pv.data || "")}" aria-label="Data do pagamento">
      </div>`;
    } else if (c.tipo === "texto") {
      html = `<p class="ajuda" style="margin:0">${c.html}</p>`;
    } else {
      const extra = c.tipo === "number" ? `step="${c.step || "0.01"}" min="0"` : "";
      html = `<label>${esc(c.label)}<input type="${c.tipo || "text"}" name="${c.nome}" value="${esc(v)}" ${extra}
        ${c.obrigatorio ? "required" : ""} placeholder="${esc(c.placeholder || "")}"></label>`;
    }
    cont.insertAdjacentHTML("beforeend", `<div class="campo" data-campo="${c.nome || ""}">${html}</div>`);
  }
  const coletar = () => {
    const dados = {};
    for (const c of campos) {
      if (!c.nome || c.tipo === "texto") continue;
      const el = cont.querySelector(`[name="${c.nome}"]`);
      if (c.tipo === "checkbox") dados[c.nome] = el.checked;
      else if (c.tipo === "pagamento") dados[c.nome] = { pago: el.checked, data: cont.querySelector(`[name="${c.nome}_data"]`).value };
      else if (c.tipo === "moeda") {
        const n = lerMoeda(el.value);
        dados[c.nome] = n === "" && !c.obrigatorio && !c.vazioNulo ? 0 : n;
      } else dados[c.nome] = el.value;
    }
    return dados;
  };
  modal._aoSalvar = () => aoSalvar(coletar());

  // Campos condicionais (mostrarSe) + prévia ao vivo (ex.: impacto de uma parcela na sobra do mês)
  const prev = $("#modal-preview");
  const atualizar = (e) => {
    // marcar uma parcela como paga preenche a data automaticamente
    const t = e?.target;
    if (t?.type === "checkbox" && t.dataset.dataPadrao !== undefined) {
      const data = cont.querySelector(`[name="${t.name}_data"]`);
      if (t.checked && !data.value) data.value = t.dataset.dataPadrao;
      if (!t.checked) data.value = "";
    }
    if (t?.type === "date" && t.name.endsWith("_data") && t.value) {
      const chk = cont.querySelector(`[name="${t.name.slice(0, -5)}"]`);
      if (chk) chk.checked = true;
    }
    const dados = coletar();
    for (const c of campos) {
      if (!c.mostrarSe) continue;
      const visivel = c.mostrarSe(dados);
      const wrap = cont.querySelector(`[data-campo="${c.nome}"]`);
      wrap.hidden = !visivel;
      wrap.querySelectorAll("input, select").forEach((i) => (i.disabled = !visivel));
    }
    prev.innerHTML = preview ? preview(coletar(), cont) || "" : "";
  };
  cont.oninput = cont.onchange = atualizar;
  atualizar();
  modal.showModal();
  cont.querySelector("input:not([disabled]), select:not([disabled])")?.focus();
}

$("#modal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const modal = $("#modal");
  try {
    await modal._aoSalvar();
    modal.close();
    toast("Salvo!");
    carregarAba();
  } catch (err) {
    $("#modal-erro").textContent = err.message;
  }
});
$("#modal-cancelar").addEventListener("click", () => $("#modal").close());

async function confirmarExcluir(recurso, id, nome) {
  if (!confirm(`Excluir "${nome}"?`)) return;
  try {
    await api.excluir(recurso, id);
    toast("Excluído.");
    carregarAba();
  } catch (err) {
    toast(err.message);
  }
}

// ================= navegação =================
function trocarAba(aba) {
  estado.aba = aba;
  document.querySelectorAll(".nav-item").forEach((b) => {
    b.classList.toggle("ativo", b.dataset.aba === aba);
    if (b.dataset.aba === aba) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  document.querySelectorAll(".aba").forEach((s) => s.classList.toggle("ativa", s.id === `aba-${aba}`));
  $("#titulo-aba").textContent = TITULOS[aba];
  $(".seletor-mes").style.visibility = aba === "simulador" ? "hidden" : "visible";
  try { localStorage.setItem("aba", aba); } catch {}
  window.scrollTo({ top: 0 });
  carregarAba();
}

async function carregarAba() {
  try {
    estado.categorias = await api.listar("categorias");
    const fn = { painel: renderPainel, fixos: renderFixos, lancamentos: renderLancamentos,
      objetivos: renderObjetivos, simulador: renderSimulador, dicas: renderDicas }[estado.aba];
    await fn();
  } catch (err) {
    if (!estado.offline) toast("Erro: " + err.message);
  }
}

// Servidor desligado: mostra aviso e tenta reconectar a cada 3 s
window.addEventListener("servidor-offline", () => {
  if (estado.offline) return;
  estado.offline = true;
  $("#offline-banner").hidden = false;
  estado.reconectar = setInterval(async () => {
    try {
      await fetch("/api/v1/config");
      clearInterval(estado.reconectar);
      estado.offline = false;
      $("#offline-banner").hidden = true;
      toast("Servidor conectado!");
      carregarAba();
    } catch {}
  }, 3000);
});

document.querySelectorAll(".nav-item").forEach((b) => b.addEventListener("click", () => trocarAba(b.dataset.aba)));
document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => trocarAba(b.dataset.ir)));

function setMes(m) {
  estado.mes = m;
  $("#mes").value = m;
  carregarAba();
}
$("#mes").addEventListener("change", (e) => e.target.value && setMes(e.target.value));
$("#mes-anterior").addEventListener("click", () => setMes(deslocarMes(estado.mes, -1)));
$("#mes-proximo").addEventListener("click", () => setMes(deslocarMes(estado.mes, 1)));

// tema claro/escuro
function aplicarTema(t) {
  if (t) document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
}
$("#tema").addEventListener("click", () => {
  const escuroAgora = getComputedStyle(document.documentElement).colorScheme === "dark";
  const novo = escuroAgora ? "light" : "dark";
  aplicarTema(novo);
  try { localStorage.setItem("tema", novo); } catch {}
  carregarAba();
});

// ================= gráficos =================
function corCSS(nome) {
  return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}
function grafico(id, config) {
  if (!window.Chart) return;
  estado.graficos[id]?.destroy();
  Chart.defaults.color = corCSS("--texto-2");
  Chart.defaults.borderColor = corCSS("--grade");
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  estado.graficos[id] = new Chart(document.getElementById(id), config);
}

// ================= PAINEL =================
async function renderPainel() {
  const [r, plano, fluxo] = await Promise.all([api.resumo(estado.mes), api.plano(estado.mes), api.fluxo(estado.mes)]);
  renderFluxo(fluxo);

  $("#kpi-renda").textContent = brl(r.renda);
  $("#kpi-renda-det").textContent = `fixa ${brl(r.renda_fixa)} · extra ${brl(r.renda_variavel)}`;
  $("#kpi-gastos").textContent = brl(r.gastos);
  $("#kpi-gastos-det").textContent = `fixos ${brl(r.despesas_fixas)} · parcelas ${brl(r.parcelas)} · avulsos ${brl(r.despesas_variaveis)}`;
  const saldo = $("#kpi-saldo");
  saldo.textContent = brl(r.saldo);
  saldo.className = "kpi-valor " + (r.saldo < 0 ? "negativo" : "positivo");
  const pct = $("#kpi-pct");
  pct.textContent = `${r.percentual_comprometido.toLocaleString("pt-BR")}%`;
  const classe = { ok: "positivo", atencao: "atencao", vermelho: "negativo" }[r.status];
  pct.className = "kpi-valor " + classe;
  const barra = $("#kpi-pct-barra");
  barra.style.width = Math.min(r.percentual_comprometido, 100) + "%";
  barra.style.background = corCSS({ ok: "--verde", atencao: "--amarelo", vermelho: "--vermelho" }[r.status]);

  const banner = $("#status-banner");
  if (r.renda === 0 && r.gastos === 0) {
    banner.innerHTML = aviso("info", "info", `Comece cadastrando sua renda e contas na aba <b>Fixos</b>.`);
  } else {
    banner.innerHTML = {
      ok: aviso("ok", "ok", `<b>Tudo certo!</b> Sobram ${brl(r.saldo)} este mês (${(100 - r.percentual_comprometido).toFixed(0)}% da renda).`),
      atencao: aviso("atencao", "alerta", `<b>Atenção:</b> ${r.percentual_comprometido.toLocaleString("pt-BR")}% da renda está comprometida. Sobram só ${brl(r.saldo)}.`),
      vermelho: aviso("vermelho", "alerta", `<b>No vermelho:</b> os gastos passam a renda em ${brl(-r.saldo)}. Veja a aba Dicas.`),
    }[r.status];
  }

  // rosca por categoria
  const cats = r.por_categoria;
  const lista = $("#lista-categorias");
  if (!cats.length) {
    lista.innerHTML = `<li class="vazio" style="display:block">Nenhum gasto neste mês.</li>`;
    estado.graficos["graf-categorias"]?.destroy();
  } else {
    grafico("graf-categorias", {
      type: "doughnut",
      data: { labels: cats.map((c) => c.nome), datasets: [{ data: cats.map((c) => c.valor), backgroundColor: cats.map((c) => corCategoria(c.cor)), borderColor: corCSS("--card-solido"), borderWidth: 2, hoverOffset: 4 }] },
      options: { maintainAspectRatio: false, cutout: "65%", plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${brl(ctx.raw)}` } } } },
    });
    lista.innerHTML = cats.map((c) => `
      <li><span class="ponto" style="background:${esc(corCategoria(c.cor))}"></span>
        <span>${esc(c.nome)} ${c.essencial ? "" : '<span class="tag">não essencial</span>'}</span>
        <strong>${brl(c.valor)}</strong>
        <span class="pct">${r.gastos ? ((c.valor / r.gastos) * 100).toFixed(0) : 0}%</span></li>`).join("");
  }

  // histórico
  grafico("graf-historico", {
    type: "bar",
    data: {
      labels: r.historico.map((h) => nomeMes(h.mes)),
      datasets: [
        { label: "Renda", data: r.historico.map((h) => h.renda), backgroundColor: corCSS("--serie-1"), borderRadius: 4, maxBarThickness: 28 },
        { label: "Gastos", data: r.historico.map((h) => h.gastos), backgroundColor: corCSS("--serie-2"), borderRadius: 4, maxBarThickness: 28 },
      ],
    },
    options: {
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, suggestedMax: 1000, ticks: { callback: (v) => brl(v).replace(",00", "") } } },
      plugins: { tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${brl(ctx.raw)}` } } },
    },
  });

  // objetivos resumidos
  const po = $("#painel-objetivos");
  if (!plano.objetivos.length) {
    po.innerHTML = `<p class="vazio">Nenhum objetivo ainda. Que tal cadastrar uma viagem ou um carro? <button class="btn-link" onclick="trocarAba('objetivos')">Criar objetivo</button></p>`;
  } else {
    po.innerHTML = plano.objetivos.map((o) => `
      <div class="mini-obj">
        <span class="obj-icone">${iconeObjetivo(o.icone)}</span>
        <div><strong>${esc(o.nome)}</strong>
          <div class="barra"><div class="barra-fill" style="width:${Math.min(o.progresso, 100)}%"></div></div>
          <small style="color:var(--texto-2)">${brl(o.valor_guardado)} de ${brl(o.valor_alvo)}</small></div>
        <small style="text-align:right">${o.falta > 0 ? (o.conclusao_em_sequencia ? `pronto em<br><b>${nomeMes(o.conclusao_em_sequencia)}</b>` : "sem sobra<br>p/ guardar") : `<span class="positivo">${ic("ok")} concluído</span>`}</small>
      </div>`).join("");
  }
}

// Fluxo diário: saldo acumulado dia a dia (começando do zero no dia 1)
function renderFluxo(f) {
  const caixa = $("#fluxo-aviso");
  const lista = $("#fluxo-lista");
  if (!f.eventos.length && !f.sem_dia.length) {
    caixa.innerHTML = "";
    lista.innerHTML = `<li class="vazio" style="display:block">Cadastre renda e contas com o dia de recebimento/vencimento para ver o fluxo.</li>`;
    estado.graficos["graf-fluxo"]?.destroy();
    return;
  }

  const p = f.periodos_negativos;
  const rendaSemDia = f.sem_dia.filter((e) => e.valor > 0);
  const contasSemDia = f.sem_dia.filter((e) => e.valor < 0);
  if (rendaSemDia.length) {
    caixa.innerHTML = aviso("atencao fluxo-aviso", "calendario", `Informe o <b>dia em que recebe</b>
      ${rendaSemDia.map((e) => esc(e.descricao)).join(", ")} (aba Fixos → editar) para eu mostrar em quais dias vai ter ou faltar dinheiro.
      ${contasSemDia.length ? `Faltam também os vencimentos de ${contasSemDia.length} conta(s)/parcela(s).` : ""}`);
  } else if (p.length) {
    const txt = p.map((x) => (x.de === x.ate ? `no dia ${x.de}` : `do dia ${x.de} ao ${x.ate}`)).join(" e ");
    caixa.innerHTML = aviso("vermelho fluxo-aviso", "alerta", `<b>Vai faltar dinheiro ${txt}.</b> O pior momento é o dia ${f.dia_menor_saldo} (${brl(f.menor_saldo)}).
      Para não ficar no vermelho, tenha <b>${brl(-f.menor_saldo)}</b> na conta no início do mês ou mude vencimentos para depois do dia em que recebe.`);
  } else {
    caixa.innerHTML = aviso("ok fluxo-aviso", "ok", `O dinheiro entra antes das contas vencerem: o saldo não fica negativo em nenhum dia do mês.
      ${contasSemDia.length ? ` (${contasSemDia.length} conta(s)/parcela(s) sem dia de vencimento não entram nessa análise.)` : ""}`);
  }

  const ehMesAtual = f.mes === hojeISO().slice(0, 7);
  const diaHoje = Number(hojeISO().slice(8, 10));
  const verde = corCSS("--serie-1"), vermelho = corCSS("--serie-8"); // polaridade: azul = saldo positivo, vermelho = negativo
  grafico("graf-fluxo", {
    type: "line",
    data: {
      labels: f.dias.map((d) => d.dia),
      datasets: [{
        label: "Saldo",
        data: f.dias.map((d) => d.saldo),
        stepped: true,
        borderWidth: 2,
        pointRadius: f.dias.map((d) => (ehMesAtual && d.dia === diaHoje ? 5 : 0)),
        fill: { target: "origin", above: verde + "33", below: vermelho + "33" },
        segment: { borderColor: (ctx) => (ctx.p1.parsed.y < 0 ? vermelho : verde) },
        borderColor: verde,
      }],
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: {
          title: (it) => `Dia ${it[0].label}${ehMesAtual && +it[0].label === diaHoje ? " (hoje)" : ""}`,
          label: (ctx) => ` Saldo: ${brl(ctx.raw)}`,
          afterLabel: (ctx) => f.eventos.filter((e) => e.dia === +ctx.label).map((e) => ` ${e.valor > 0 ? "+" : "−"} ${brl(Math.abs(e.valor))} ${e.descricao}`),
        } },
      },
      scales: {
        x: { title: { display: true, text: "dia do mês" }, ticks: { maxTicksLimit: 16 } },
        y: { ticks: { callback: (v) => brl(v).replace(",00", "") } },
      },
    },
  });

  const icone = { receita: "entrada", conta: "casa", parcela: "cartao", avulso: "recibo" };
  const linha = (e, semDia) => {
    const extra = [e.parte, e.parcela && `parcela ${e.parcela}`, e.pago_em && `paga em ${dataBR(e.pago_em)}`].filter(Boolean).join(" · ");
    return `<li class="${ehMesAtual && e.dia === diaHoje ? "hoje" : ""}">
      <span class="fluxo-dia">${semDia ? "—" : String(e.dia).padStart(2, "0")}<small>${semDia ? "sem dia" : MESES[Number(f.mes.slice(5)) - 1]}</small></span>
      <span class="desc">${ic(icone[e.tipo] || "recibo", "ic-sm")}<span>${esc(e.descricao)}${extra ? `<small>${esc(extra)}${e.pago_em ? " " + ic("check", "ic-sm positivo") : ""}</small>` : ""}</span></span>
      <span class="val ${e.valor > 0 ? "positivo" : "negativo"}">${e.valor > 0 ? "+" : "−"} ${brl(Math.abs(e.valor))}
        ${semDia ? "" : `<small class="${e.saldo_apos < 0 ? "neg" : ""}">saldo ${brl(e.saldo_apos)}</small>`}</span>
    </li>`;
  };
  lista.innerHTML = f.eventos.map((e) => linha(e, false)).join("") +
    (f.sem_dia.length
      ? `<li style="display:block;border:0;padding-top:14px"><small style="color:var(--texto-2)">Sem dia definido (edite para informar o dia e ver no gráfico):</small></li>` +
        f.sem_dia.map((e) => linha(e, true)).join("")
      : "");
}

// ================= FIXOS =================
function descreverRecebimento(x) {
  if ((x.valor_2 || 0) > 0) {
    const partes = [[x.dia_recebimento, x.valor - x.valor_2], [x.dia_recebimento_2, x.valor_2]]
      .sort((a, b) => (a[0] || 99) - (b[0] || 99));
    return partes.map(([d, v]) => `${d ? `dia ${d}` : "sem dia"}: ${brl(v)}`).join(" · ");
  }
  return x.dia_recebimento ? `recebe todo dia ${x.dia_recebimento}` : "dia de recebimento não informado";
}

async function renderFixos() {
  const [receitas, despesas] = await Promise.all([api.listar("receitas-fixas"), api.listar("despesas-fixas"), renderParcelamentos()]);

  $("#lista-receitas").innerHTML = receitas.length ? receitas.map((x) => `
    <li class="${x.ativo ? "" : "inativo"}">
      <div class="info"><strong>${esc(x.descricao)}</strong><small>${descreverRecebimento(x)}${x.ativo ? "" : " · pausada"}</small></div>
      <span class="valor positivo">${brl(x.valor)}</span>
      <div class="acoes"><button title="Editar" aria-label="Editar ${esc(x.descricao)}" data-editar-receita="${x.id}">${ic("lapis")}</button><button class="perigo" title="Excluir" aria-label="Excluir ${esc(x.descricao)}" data-excluir-receita="${x.id}">${ic("lixo")}</button></div>
    </li>`).join("") : `<li class="vazio">Nenhuma renda cadastrada.</li>`;
  $("#total-receitas").textContent = brl(receitas.filter((x) => x.ativo).reduce((s, x) => s + x.valor, 0));

  $("#lista-despesas").innerHTML = despesas.length ? despesas.map((x) => {
    const cat = catPorId(x.categoria_id);
    return `
    <li class="${x.ativo ? "" : "inativo"}">
      <span class="ponto" style="background:${esc(corCategoria(cat?.cor))}"></span>
      <div class="info"><strong>${esc(x.descricao)}</strong>
        <small>${esc(cat?.nome || "Sem categoria")}${x.dia_vencimento ? ` · vence dia ${x.dia_vencimento}` : ""}${x.ativo ? "" : " · pausada"}</small></div>
      <span class="valor negativo">${brl(x.valor)}</span>
      <div class="acoes"><button title="Editar" aria-label="Editar ${esc(x.descricao)}" data-editar-despesa="${x.id}">${ic("lapis")}</button><button class="perigo" title="Excluir" aria-label="Excluir ${esc(x.descricao)}" data-excluir-despesa="${x.id}">${ic("lixo")}</button></div>
    </li>`;
  }).join("") : `<li class="vazio">Nenhuma conta fixa cadastrada.</li>`;
  $("#total-despesas").textContent = brl(despesas.filter((x) => x.ativo).reduce((s, x) => s + x.valor, 0));

  $("#lista-cat-edit").innerHTML = estado.categorias.map((c) => `
    <button class="chip" data-editar-cat="${c.id}"><span class="ponto" style="background:${esc(corCategoria(c.cor))}"></span>${esc(c.nome)}${c.essencial ? `${ic("estrela", "ic-sm")}<span class="sr-only">(essencial)</span>` : ""}</button>`).join("");

  const formReceita = (x = {}) => {
    const dividido = (x.valor_2 || 0) > 0;
    const ehDividido = (d) => d.forma === "dividido";
    abrirFormulario({
      titulo: x.id ? "Editar renda" : "Nova renda fixa",
      valores: {
        ...x,
        forma: dividido ? "dividido" : "unico",
        valor_unico: dividido ? "" : x.valor,
        dia_unico: x.dia_recebimento,
        valor_p1: dividido ? x.valor - x.valor_2 : "",
        dia_p1: x.dia_recebimento,
        valor_p2: dividido ? x.valor_2 : "",
        dia_p2: x.dia_recebimento_2,
      },
      campos: [
        { nome: "descricao", label: "Descrição", obrigatorio: true, placeholder: "Ex.: Salário" },
        { nome: "forma", label: "Como você recebe?", tipo: "select", padrao: "unico", opcoes: [
          { valor: "unico", texto: "Tudo de uma vez, em um dia" },
          { valor: "dividido", texto: "Em duas datas (ex.: adiantamento + restante)" }] },
        { nome: "valor_unico", label: "Valor mensal", tipo: "moeda", mostrarSe: (d) => !ehDividido(d) },
        { nome: "dia_unico", label: "Dia que recebe", tipo: "inteiro", max: 31, placeholder: "ex.: 5", mostrarSe: (d) => !ehDividido(d) },
        { nome: "valor_p1", label: "Valor do 1º pagamento", tipo: "moeda", mostrarSe: ehDividido },
        { nome: "dia_p1", label: "Dia do 1º pagamento", tipo: "inteiro", max: 31, placeholder: "ex.: 5", mostrarSe: ehDividido },
        { nome: "valor_p2", label: "Valor do 2º pagamento (adiantamento)", tipo: "moeda", mostrarSe: ehDividido },
        { nome: "dia_p2", label: "Dia do 2º pagamento", tipo: "inteiro", max: 31, placeholder: "ex.: 20", mostrarSe: ehDividido },
        { nome: "ativo", label: "Ativa (entra no cálculo)", tipo: "checkbox", padrao: true },
      ],
      preview: (d) => {
        if (!ehDividido(d)) {
          return d.valor_unico && d.dia_unico ? `<div class="linha"><span>Você recebe</span><strong class="positivo">${brl(d.valor_unico)} todo dia ${d.dia_unico}</strong></div>` : "";
        }
        const total = (Number(d.valor_p1) || 0) + (Number(d.valor_p2) || 0);
        if (!total) return "";
        const partes = [[d.dia_p1, d.valor_p1], [d.dia_p2, d.valor_p2]].filter((p) => p[1]).sort((a, b) => (+a[0] || 99) - (+b[0] || 99));
        return partes.map(([dia, v]) => `<div class="linha"><span>${dia ? `Dia ${dia}` : "Dia não informado"}</span><strong class="positivo">+ ${brl(v)}</strong></div>`).join("") +
          `<div class="linha destaque-impacto"><span>Total no mês</span><strong>${brl(total)}</strong></div>`;
      },
      aoSalvar: (d) => {
        let dados;
        if (ehDividido(d)) {
          const v1 = Number(d.valor_p1) || 0, v2 = Number(d.valor_p2) || 0;
          if (!v1 || !v2) throw new Error("Preencha o valor dos dois pagamentos.");
          if (!d.dia_p1 || !d.dia_p2) throw new Error("Preencha o dia dos dois pagamentos.");
          dados = { valor: v1 + v2, dia_recebimento: d.dia_p1, valor_2: v2, dia_recebimento_2: d.dia_p2 };
        } else {
          if (!Number(d.valor_unico)) throw new Error("Preencha o valor mensal.");
          dados = { valor: d.valor_unico, dia_recebimento: d.dia_unico, valor_2: 0, dia_recebimento_2: null };
        }
        dados = { descricao: d.descricao, ativo: d.ativo, ...dados };
        return x.id ? api.atualizar("receitas-fixas", x.id, dados) : api.criar("receitas-fixas", dados);
      },
    });
  };
  const formDespesa = (x = {}) => abrirFormulario({
    titulo: x.id ? "Editar conta fixa" : "Nova conta fixa",
    valores: x,
    campos: [
      { nome: "descricao", label: "Descrição", obrigatorio: true, placeholder: "Ex.: Aluguel" },
      { nome: "valor", label: "Valor mensal", tipo: "moeda", obrigatorio: true },
      { nome: "categoria_id", label: "Categoria", tipo: "select", opcoes: opcoesCategorias() },
      { nome: "dia_vencimento", label: "Dia do vencimento (opcional)", tipo: "inteiro", max: 31, placeholder: "ex.: 10" },
      { nome: "ativo", label: "Ativa (entra no cálculo)", tipo: "checkbox", padrao: true },
    ],
    aoSalvar: (d) => (x.id ? api.atualizar("despesas-fixas", x.id, d) : api.criar("despesas-fixas", d)),
  });
  const formCategoria = (x = {}) => abrirFormulario({
    titulo: x.id ? "Editar categoria" : "Nova categoria",
    valores: x,
    campos: [
      { nome: "nome", label: "Nome", obrigatorio: true },
      { nome: "cor", label: "Cor", tipo: "color", padrao: "#64748b" },
      { nome: "essencial", label: "Essencial (necessidade básica)", tipo: "checkbox" },
    ],
    aoSalvar: (d) => (x.id ? api.atualizar("categorias", x.id, d) : api.criar("categorias", d)),
  });

  $("#nova-receita").onclick = () => formReceita();
  $("#nova-despesa").onclick = () => formDespesa();
  $("#nova-categoria").onclick = () => formCategoria();
  $("#aba-fixos").onclick = (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const d = b.dataset;
    if (d.editarReceita) formReceita(receitas.find((x) => x.id == d.editarReceita));
    if (d.excluirReceita) confirmarExcluir("receitas-fixas", d.excluirReceita, receitas.find((x) => x.id == d.excluirReceita).descricao);
    if (d.editarDespesa) formDespesa(despesas.find((x) => x.id == d.editarDespesa));
    if (d.excluirDespesa) confirmarExcluir("despesas-fixas", d.excluirDespesa, despesas.find((x) => x.id == d.excluirDespesa).descricao);
    if (d.editarCat) formCategoria(estado.categorias.find((x) => x.id == d.editarCat));
  };
}

// ================= PARCELAMENTOS E DÍVIDAS =================
async function renderParcelamentos() {
  const [itens, resumo, proj] = await Promise.all([
    api.listar("parcelamentos", { mes: estado.mes }),
    api.resumo(estado.mes),
    api.projecao(estado.mes, 6),
  ]);

  const ativos = itens.filter((p) => p.status === "ativo");
  const devendo = itens.reduce((s, p) => s + p.valor_restante, 0);
  const atrasado = itens.reduce((s, p) => s + p.valor_atrasado, 0);
  $("#parcelas-resumo").innerHTML = itens.length ? `
    <div class="mini-kpi"><small>Parcelas em ${nomeMes(estado.mes)}</small><strong class="negativo">${brl(resumo.parcelas)}</strong></div>
    <div class="mini-kpi"><small>Ainda a pagar (parcelas não pagas)</small><strong>${brl(devendo)}</strong></div>
    <div class="mini-kpi"><small>Sobra do mês com as parcelas</small><strong class="${resumo.saldo < 0 ? "negativo" : "positivo"}">${brl(resumo.saldo)}</strong></div>
    ${atrasado > 0
      ? `<div class="mini-kpi alerta"><small>${ic("alerta","ic-sm")} Atrasado</small><strong class="negativo">${brl(atrasado)}</strong></div>`
      : `<div class="mini-kpi"><small>Parcelas ativas</small><strong>${ativos.length}</strong></div>`}` : "";

  const statusTxt = (p) => {
    if (p.parcelas_restantes === 0) return `<span class="tag quitado">${ic("check","ic-sm")} tudo pago</span>`;
    let t = p.status === "ativo" ? `parcela ${p.parcela_atual}/${p.num_parcelas} ${p.parcela_atual_paga ? `<span class="tag paga">${ic("check","ic-sm")} paga</span>` : `vence ${dataBR(p.vencimento_no_mes)}`}`
      : p.status === "futuro" ? `<span class="tag futuro">começa em ${nomeMes(p.primeira_parcela)}</span>`
      : `<span class="tag">período encerrado</span>`;
    if (p.parcelas_atrasadas) t += ` <span class="tag atrasada">${ic("alerta","ic-sm")} ${p.parcelas_atrasadas} atrasada(s)</span>`;
    return t;
  };

  $("#lista-parcelamentos").innerHTML = itens.length ? itens.map((p) => {
    const cat = catPorId(p.categoria_id);
    return `
    <li class="parcela-item ${p.status === "quitado" ? "inativo" : ""}">
      <span class="ponto" style="background:${esc(corCategoria(cat?.cor))}"></span>
      <div class="info">
        <strong>${ic(p.tipo === "divida" ? "cartao" : "sacola", "ic-sm")}${esc(p.descricao)}</strong>
        <small>${p.num_parcelas}x de ${brl(p.valor_parcela)}${p.dia_vencimento ? ` · cobrada todo dia ${p.dia_vencimento}` : ""} · total ${brl(p.total_a_pagar)}${p.juros > 0 ? ` (juros ${brl(p.juros)})` : ""}</small>
        <div class="barra"><div class="barra-fill" style="width:${p.progresso}%"></div></div>
        <small><b>${p.parcelas_pagas} de ${p.num_parcelas} pagas</b>${p.ultimo_pagamento ? ` (última em ${dataBR(p.ultimo_pagamento)})` : ""}${p.valor_restante > 0 ? ` · falta ${brl(p.valor_restante)}` : ""}</small>
        <small>${statusTxt(p)} · termina em ${nomeMes(p.ultima_parcela)}</small>
      </div>
      <span class="valor ${p.status === "ativo" ? "negativo" : ""}">${brl(p.valor_no_mes)} <small style="font-weight:400;color:var(--texto-2)">neste mês</small></span>
      <div class="acoes"><button title="Registrar pagamentos" aria-label="Registrar pagamentos de ${esc(p.descricao)}" data-pagar-parc="${p.id}">${ic("dinheiro")}</button><button title="Editar" aria-label="Editar ${esc(p.descricao)}" data-editar-parc="${p.id}">${ic("lapis")}</button><button class="perigo" title="Excluir" aria-label="Excluir ${esc(p.descricao)}" data-excluir-parc="${p.id}">${ic("lixo")}</button></div>
    </li>`;
  }).join("") : `<li class="vazio">Nenhuma compra parcelada ou dívida cadastrada.</li>`;

  // projeção dos próximos meses: barras verdes (sobra) / vermelhas (falta)
  grafico("graf-projecao", {
    type: "bar",
    data: {
      labels: proj.map((m) => nomeMes(m.mes)),
      datasets: [{
        label: "Sobra / falta",
        data: proj.map((m) => m.saldo),
        backgroundColor: proj.map((m) => corCSS(m.saldo < 0 ? "--serie-8" : "--serie-1")),
        borderRadius: 4, maxBarThickness: 36,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => {
          const m = proj[ctx.dataIndex];
          return [` ${m.saldo < 0 ? "Falta" : "Sobra"}: ${brl(Math.abs(m.saldo))}`, ` Parcelas: ${brl(m.parcelas)}`, ` Gastos: ${brl(m.gastos)}`];
        } } },
      },
      scales: { y: { suggestedMax: 1000, ticks: { callback: (v) => brl(v).replace(",00", "") } } },
    },
  });

  $("#novo-parcelamento").onclick = () => formParcelamento({}, resumo);
  $("#lista-parcelamentos").onclick = (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const p = itens.find((x) => x.id == (b.dataset.editarParc || b.dataset.excluirParc || b.dataset.pagarParc));
    if (b.dataset.pagarParc) formPagamentos(p);
    if (b.dataset.editarParc) formParcelamento(p, resumo);
    if (b.dataset.excluirParc) confirmarExcluir("parcelamentos", p.id, p.descricao);
  };
}

function formParcelamento(p, resumo) {
  // sobra do mês SEM este parcelamento (ao editar, devolve a parcela atual dele)
  const sobraBase = resumo.saldo + (p.status === "ativo" ? p.valor_parcela : 0);
  abrirFormulario({
    titulo: p.id ? "Editar parcelamento" : "Nova compra parcelada / dívida",
    valores: p,
    campos: [
      { nome: "tipo", label: "Tipo", tipo: "select", padrao: "compra", opcoes: [
        { valor: "compra", texto: "Compra parcelada" }, { valor: "divida", texto: "Dívida / empréstimo / financiamento" }] },
      { nome: "descricao", label: "Descrição", obrigatorio: true, placeholder: "Ex.: Notebook, Cartão, Empréstimo" },
      { nome: "valor_total", label: "Valor total da compra/dívida", tipo: "moeda", obrigatorio: true },
      { nome: "num_parcelas", label: "Número de parcelas", tipo: "inteiro", sufixo: "parcelas", obrigatorio: true, max: 600, placeholder: "ex.: 10" },
      { nome: "valor_parcela", label: "Valor de cada parcela (deixe vazio para dividir o total)", tipo: "moeda", vazioNulo: true, placeholder: "automático" },
      { nome: "primeira_parcela", label: "Mês da 1ª parcela", tipo: "month", obrigatorio: true, padrao: estado.mes },
      { nome: "dia_vencimento", label: "Dia do mês em que é cobrada (vencimento)", tipo: "inteiro", max: 31, placeholder: "ex.: 10" },
      ...(p.id ? [] : [{ nome: "ja_pagas", label: "Quantas parcelas você já pagou?", tipo: "inteiro", min: 0, max: 600, padrao: 0,
        placeholder: "0" }]),
      { nome: "categoria_id", label: "Categoria", tipo: "select", opcoes: opcoesCategorias() },
      ...(p.id ? [{ tipo: "texto", html: "Para marcar quais parcelas já foram pagas e em que dia, use o botão de pagamentos (ícone de dinheiro) na lista." }] : []),
    ],
    preview: (d) => {
      const total = Number(d.valor_total) || 0;
      const n = parseInt(d.num_parcelas) || 0;
      if (!total || !n) return `<span style="color:var(--texto-2)">Preencha o valor total e o número de parcelas para ver o impacto no seu mês.</span>`;
      const parcela = d.valor_parcela !== "" && Number(d.valor_parcela) > 0 ? Number(d.valor_parcela) : Math.round((total / n) * 100) / 100;
      const pagar = parcela * n;
      const juros = pagar - total;
      const ultima = d.primeira_parcela ? deslocarMes(d.primeira_parcela, n - 1) : null;
      const depois = sobraBase - parcela;
      return `
        <div class="linha"><span>Parcela</span><strong>${n}x de ${brl(parcela)}</strong></div>
        <div class="linha"><span>Total a pagar</span><strong>${brl(pagar)}</strong></div>
        ${juros > 0.005 ? `<div class="linha"><span>Juros</span><strong class="negativo">${brl(juros)} (${((juros / total) * 100).toFixed(1).replace(".", ",")}%)</strong></div>` : ""}
        ${ultima ? `<div class="linha"><span>Período</span><strong>${nomeMes(d.primeira_parcela)} → ${nomeMes(ultima)}</strong></div>` : ""}
        <div class="linha"><span>Sua sobra em ${nomeMes(estado.mes)} sem esta parcela</span><strong>${brl(sobraBase)}</strong></div>
        <div class="linha destaque-impacto"><span>Com esta parcela</span>
          <strong class="${depois < 0 ? "negativo" : "positivo"}">${depois < 0 ? `faltam ${brl(-depois)}/mês` : `sobram ${brl(depois)}/mês`}</strong></div>`;
    },
    aoSalvar: async (d) => {
      const { ja_pagas, ...dados } = d;
      if (p.id) return api.atualizar("parcelamentos", p.id, dados);
      const novo = await api.criar("parcelamentos", dados);
      // parcelas já pagas: registra com a data de vencimento de cada uma (dá para ajustar no botão de pagamentos)
      const k = Math.min(parseInt(ja_pagas) || 0, novo.num_parcelas);
      if (k > 0) {
        const lista = await api.pagamentos(novo.id);
        await api.salvarPagamentos(novo.id, lista.slice(0, k).map((x) => ({ numero: x.numero, data_pagamento: x.vencimento })));
      }
      return novo;
    },
  });
}

// Marcar quais parcelas foram pagas e em que dia
async function formPagamentos(p) {
  const lista = await api.pagamentos(p.id);
  const hoje = hojeISO();
  abrirFormulario({
    titulo: `Pagamentos: ${p.descricao}`,
    campos: [
      { tipo: "texto", html: "Marque as parcelas pagas e ajuste a data em que pagou. Ao marcar, a data do vencimento é preenchida (ou hoje, se ainda não venceu)." },
      ...lista.map((x) => ({
        nome: `p_${x.numero}`,
        tipo: "pagamento",
        label: `Parcela ${x.numero}/${lista.length} · ${nomeMes(x.mes)}`,
        detalhe: ` vence ${dataBR(x.vencimento)} · ${brl(x.valor)}${!x.pago && x.vencimento < hoje ? " · atrasada" : ""}`,
        dataPadrao: x.vencimento <= hoje ? x.vencimento : hoje,
        valor: { pago: x.pago, data: x.data_pagamento, atrasada: !x.pago && x.vencimento < hoje },
      })),
    ],
    preview: (d) => {
      const pagas = lista.filter((x) => d[`p_${x.numero}`].pago).length;
      return `<div class="linha"><span>Pagas</span><strong>${pagas} de ${lista.length}</strong></div>
        <div class="linha destaque-impacto"><span>Falta pagar</span><strong>${brl((lista.length - pagas) * p.valor_parcela)}</strong></div>`;
    },
    aoSalvar: (d) => {
      const pagamentos = [];
      for (const x of lista) {
        const v = d[`p_${x.numero}`];
        if (!v.pago) continue;
        if (!v.data) throw new Error(`Informe a data de pagamento da parcela ${x.numero}.`);
        pagamentos.push({ numero: x.numero, data_pagamento: v.data });
      }
      return api.salvarPagamentos(p.id, pagamentos);
    },
  });
}

// ================= LANÇAMENTOS =================
async function renderLancamentos() {
  const filtro = $("#filtro-categoria");
  const atual = filtro.value;
  filtro.innerHTML = `<option value="">Todas as categorias</option>` +
    estado.categorias.map((c) => `<option value="${c.id}">${esc(c.nome)}</option>`).join("");
  filtro.value = atual;
  filtro.onchange = renderLancamentos;

  let itens = await api.listar("lancamentos", { mes: estado.mes });
  if (filtro.value) itens = itens.filter((x) => String(x.categoria_id) === filtro.value);

  $("#lista-lancamentos").innerHTML = itens.length ? itens.map((x) => {
    const cat = catPorId(x.categoria_id);
    const receita = x.tipo === "receita";
    return `
    <li>
      <span class="ponto" style="background:${receita ? corCSS("--verde") : esc(corCategoria(cat?.cor))}"></span>
      <div class="info"><strong>${esc(x.descricao)}</strong>
        <small>${x.data.split("-").reverse().join("/")} · ${receita ? "Receita" : esc(cat?.nome || "Sem categoria")}</small></div>
      <span class="valor ${receita ? "positivo" : "negativo"}">${receita ? "+" : "−"} ${brl(x.valor)}</span>
      <div class="acoes"><button title="Editar" aria-label="Editar ${esc(x.descricao)}" data-editar="${x.id}">${ic("lapis")}</button><button class="perigo" title="Excluir" aria-label="Excluir ${esc(x.descricao)}" data-excluir="${x.id}">${ic("lixo")}</button></div>
    </li>`;
  }).join("") : `<li class="vazio">Nenhum lançamento em ${nomeMes(estado.mes)}. Registre aqui gastos do dia a dia (mercado, lazer, compras...).</li>`;

  const gastos = itens.filter((x) => x.tipo === "despesa").reduce((s, x) => s + x.valor, 0);
  const receitas = itens.filter((x) => x.tipo === "receita").reduce((s, x) => s + x.valor, 0);
  $("#total-lancamentos").innerHTML = `Gastos: <strong class="negativo">${brl(gastos)}</strong> &nbsp; Receitas extras: <strong class="positivo">${brl(receitas)}</strong>`;

  const dataPadrao = estado.mes === hojeISO().slice(0, 7) ? hojeISO() : `${estado.mes}-01`;
  const form = (x = {}) => abrirFormulario({
    titulo: x.id ? "Editar lançamento" : "Novo lançamento",
    valores: x,
    campos: [
      { nome: "tipo", label: "Tipo", tipo: "select", padrao: "despesa", opcoes: [{ valor: "despesa", texto: "Gasto" }, { valor: "receita", texto: "Receita extra" }] },
      { nome: "descricao", label: "Descrição", obrigatorio: true, placeholder: "Ex.: Mercado" },
      { nome: "valor", label: "Valor", tipo: "moeda", obrigatorio: true },
      { nome: "data", label: "Data", tipo: "date", obrigatorio: true, padrao: dataPadrao },
      { nome: "categoria_id", label: "Categoria", tipo: "select", opcoes: opcoesCategorias() },
    ],
    aoSalvar: (d) => (x.id ? api.atualizar("lancamentos", x.id, d) : api.criar("lancamentos", d)),
  });
  $("#novo-lancamento").onclick = () => form();
  $("#lista-lancamentos").onclick = (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const item = itens.find((x) => x.id == (b.dataset.editar || b.dataset.excluir));
    if (b.dataset.editar) form(item);
    if (b.dataset.excluir) confirmarExcluir("lancamentos", item.id, item.descricao);
  };
}

// ================= OBJETIVOS =================
async function renderObjetivos() {
  const [plano, cfg] = await Promise.all([api.plano(estado.mes), api.config()]);

  const range = $("#pct-metas");
  range.value = parseFloat(cfg.percentual_metas);
  $("#pct-metas-valor").textContent = `${range.value}%`;
  range.oninput = () => ($("#pct-metas-valor").textContent = `${range.value}%`);
  range.onchange = async () => {
    await api.salvarConfig({ percentual_metas: range.value });
    renderObjetivos();
  };

  const pr = $("#plano-resumo");
  if (!plano.objetivos.length) {
    pr.innerHTML = `<h2>Defina seus objetivos</h2><p style="margin:0">Cadastre uma viagem, intercâmbio, carro ou casa e eu calculo quanto guardar por mês e quando você chega lá.</p>`;
  } else {
    let alertaPlano = "";
    if (plano.aporte_mensal <= 0) alertaPlano = `<p style="margin:12px 0 0">${ic("alerta")} <span>Sem sobra no mês para guardar. Reduza gastos (veja a aba Dicas) para começar a juntar.</span></p>`;
    else if (!plano.prazos_viaveis) alertaPlano = `<p style="margin:12px 0 0">${ic("alerta")} <span>Para cumprir todos os prazos você precisa guardar ${brl(plano.soma_mensal_prazos)}/mês, mas sua sobra para metas é ${brl(plano.aporte_mensal)}.</span></p>`;
    pr.innerHTML = `
      <h2>Plano para todos os objetivos</h2>
      <div class="plano-grid">
        <div><small>Falta juntar</small><span class="plano-num">${brl(plano.falta_total)}</span></div>
        <div><small>Guardando por mês</small><span class="plano-num">${brl(plano.aporte_mensal)}</span></div>
        <div><small>Tempo para tudo</small><span class="plano-num">${tempoLegivel(plano.meses_total)}</span></div>
        <div><small>Previsão</small><span class="plano-num">${plano.conclusao_total ? nomeMes(plano.conclusao_total) : "—"}</span></div>
      </div>${alertaPlano}`;
  }

  $("#lista-objetivos").innerHTML = plano.objetivos.map((o) => `
    <div class="card">
      <div class="obj-topo">
        <span class="obj-icone">${iconeObjetivo(o.icone)}</span>
        <div class="info"><strong>${esc(o.nome)}</strong><small style="color:var(--texto-2)">Prioridade ${o.prioridade}</small></div>
        <div class="acoes"><button title="Editar" aria-label="Editar ${esc(o.nome)}" data-editar="${o.id}">${ic("lapis")}</button><button class="perigo" title="Excluir" aria-label="Excluir ${esc(o.nome)}" data-excluir="${o.id}">${ic("lixo")}</button></div>
      </div>
      <div class="barra"><div class="barra-fill" style="width:${Math.min(o.progresso, 100)}%"></div></div>
      <div class="obj-linha"><span>${brl(o.valor_guardado)} de ${brl(o.valor_alvo)}</span><strong>${o.progresso}%</strong></div>
      <div class="obj-linha"><span>Falta</span><strong>${brl(o.falta)}</strong></div>
      ${o.prazo_meses ? `<div class="obj-linha"><span>Guardar por mês (prazo ${meses(o.prazo_meses)})</span><strong class="${o.viavel_no_prazo ? "positivo" : "negativo"}">${brl(o.mensal_necessario)}</strong></div>` : ""}
      <div class="obj-linha"><span>Só nele, com a sobra atual</span><strong>${tempoLegivel(o.meses_se_unico)}</strong></div>
      <div class="obj-linha"><span>Na fila de prioridades</span><strong>${o.falta > 0 ? (o.conclusao_em_sequencia ? nomeMes(o.conclusao_em_sequencia) : "sem previsão") : `<span class="positivo">${ic("ok", "ic-sm")} concluído</span>`}</strong></div>
      <div class="obj-rodape"><button class="btn btn-sec" data-guardar="${o.id}">${ic("mais", "ic-sm")}Guardei dinheiro</button></div>
    </div>`).join("");

  const form = (x = {}) => abrirFormulario({
    titulo: x.id ? "Editar objetivo" : "Novo objetivo",
    valores: x,
    campos: [
      { nome: "icone", label: "Tipo de objetivo (ícone)", tipo: "select", padrao: "🎯",
        opcoes: Object.entries(ICONES_OBJETIVO).map(([valor, [, texto]]) => ({ valor, texto })) },
      { nome: "nome", label: "Nome", obrigatorio: true, placeholder: "Ex.: Viagem para a Europa" },
      { nome: "valor_alvo", label: "Quanto custa", tipo: "moeda", obrigatorio: true },
      { nome: "valor_guardado", label: "Já tenho guardado", tipo: "moeda" },
      { nome: "prazo_meses", label: "Quero conseguir em (opcional)", tipo: "inteiro", sufixo: "meses", placeholder: "ex.: 12" },
      { nome: "prioridade", label: "Prioridade (1 = mais importante)", tipo: "inteiro", padrao: plano.objetivos.length + 1 },
    ],
    aoSalvar: (d) => (x.id ? api.atualizar("objetivos", x.id, d) : api.criar("objetivos", d)),
  });
  $("#novo-objetivo").onclick = () => form();
  $("#lista-objetivos").onclick = (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const o = plano.objetivos.find((x) => x.id == (b.dataset.editar || b.dataset.excluir || b.dataset.guardar));
    if (b.dataset.editar) form(o);
    if (b.dataset.excluir) confirmarExcluir("objetivos", o.id, o.nome);
    if (b.dataset.guardar) abrirFormulario({
      titulo: `Guardar para ${o.nome}`,
      campos: [{ nome: "valor", label: "Quanto você guardou?", tipo: "moeda", obrigatorio: true }],
      aoSalvar: (d) => api.atualizar("objetivos", o.id, { valor_guardado: o.valor_guardado + (Number(d.valor) || 0) }),
    });
  };
}

// ================= SIMULADOR =================
function adicionarMetaSim(nome = "", valor = "") {
  const div = document.createElement("div");
  div.className = "sim-meta";
  div.innerHTML = `<input placeholder="Meta (ex.: Intercâmbio)" value="${esc(nome)}" class="sim-nome">
    ${htmlMoeda({ classe: "sim-valor", valor })}
    <button type="button" title="Remover" aria-label="Remover meta">${ic("x")}</button>`;
  div.querySelector("button").onclick = () => div.remove();
  $("#sim-metas").appendChild(div);
}

let simuladorIniciado = false;
async function renderSimulador() {
  if (simuladorIniciado) return;
  simuladorIniciado = true;
  adicionarMetaSim("Viagem", "");
  adicionarMetaSim("Intercâmbio", "");
  $("#sim-add").onclick = () => adicionarMetaSim();
  $("#sim-usar-sobra").onclick = async () => {
    const plano = await api.plano(hojeISO().slice(0, 7));
    $("#sim-aporte").value = moedaParaTexto(plano.aporte_mensal);
    toast(`Sobra para metas: ${brl(plano.aporte_mensal)}/mês`);
  };
  $("#sim-calcular").onclick = calcularSimulacao;
}

async function calcularSimulacao() {
  const metas = [...document.querySelectorAll(".sim-meta")]
    .map((d) => ({ nome: d.querySelector(".sim-nome").value || "Meta", valor: lerMoeda(d.querySelector(".sim-valor").value) }))
    .filter((m) => m.valor !== "");
  const out = $("#sim-resultado");
  try {
    const r = await api.simular({
      metas,
      aporte_mensal: lerMoeda($("#sim-aporte").value),
      prazo_meses: $("#sim-prazo").value,
      ja_guardado: lerMoeda($("#sim-guardado").value),
    });
    let html = `<div class="card destaque"><h2>Total das metas: ${brl(r.total)}</h2><div class="plano-grid">
      <div><small>Falta juntar</small><span class="plano-num">${brl(r.falta)}</span></div>`;
    if (r.mensal_necessario !== undefined)
      html += `<div><small>Guardar por mês para ${meses(r.prazo_meses)}</small><span class="plano-num">${brl(r.mensal_necessario)}</span></div>`;
    if (r.meses !== undefined)
      html += `<div><small>Guardando ${brl(r.aporte_mensal)}/mês</small><span class="plano-num">${tempoLegivel(r.meses)}</span></div>
               <div><small>Previsão</small><span class="plano-num">${r.conclusao ? nomeMes(r.conclusao) : "—"}</span></div>`;
    html += `</div>`;
    if (r.cabe_no_prazo === false) html += `<p style="margin:12px 0 0">${ic("alerta")} <span>Com ${brl(r.aporte_mensal)}/mês não dá para juntar tudo em ${meses(r.prazo_meses)}. Faltariam ${brl(r.falta - r.aporte_mensal * r.prazo_meses)}.</span></p>`;
    if (r.cabe_no_prazo === true) html += `<p style="margin:12px 0 0">${ic("ok")} <span>Dá para juntar tudo dentro do prazo!</span></p>`;
    html += `</div>`;
    if (r.linha_do_tempo) {
      html += `<div class="card"><h2>Linha do tempo (juntando uma meta de cada vez)</h2><ul class="timeline">` +
        r.linha_do_tempo.map((m) => `<li><strong>${esc(m.nome)}</strong> — ${brl(m.valor)}<br>
          <small style="color:var(--texto-2)">${m.meses === 0 ? "já coberta pelo que você tem guardado" : `pronta em ${tempoLegivel(m.meses)} (${nomeMes(m.conclusao)})`}</small></li>`).join("") +
        `</ul></div>`;
    }
    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = `<div class="card"><p class="erro">${esc(err.message)}</p></div>`;
  }
}

// ================= DICAS =================
async function renderDicas() {
  const dicas = await api.sugestoes(estado.mes);
  const icone = { alerta: "alerta", dica: "lampada", info: "info", ok: "ok" };
  $("#lista-dicas").innerHTML = dicas.map((d) => `
    <div class="card dica ${d.tipo === "dica" ? "dica-tipo" : d.tipo}">
      <span class="dica-icone">${ic(icone[d.tipo] || "info")}</span>
      <div>
        <h3>${esc(d.titulo)}</h3>
        <p>${esc(d.texto)}</p>
        ${d.economia ? `<span class="economia">Economia possível: ${brl(d.economia)}/mês</span>` : ""}
      </div>
    </div>`).join("");
}

// ================= início =================
(function iniciar() {
  try {
    const t = localStorage.getItem("tema");
    if (t) aplicarTema(t);
  } catch {}
  $("#mes").value = estado.mes;
  let aba = "painel";
  try { aba = localStorage.getItem("aba") || "painel"; } catch {}
  trocarAba(TITULOS[aba] ? aba : "painel");
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).then((r) => r.update()).catch(() => {});
})();
