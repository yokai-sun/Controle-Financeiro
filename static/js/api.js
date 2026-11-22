// Cliente da API REST. Um app mobile pode consumir exatamente os mesmos endpoints.
const API_BASE = "/api/v1";

async function requisicao(metodo, caminho, corpo) {
  const opcoes = { method: metodo, headers: {} };
  if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }
  let resp;
  try {
    resp = await fetch(API_BASE + caminho, opcoes);
  } catch {
    // Rede falhou: o servidor Python não está rodando
    window.dispatchEvent(new Event("servidor-offline"));
    throw new Error("Servidor desligado. Abra o iniciar.bat (ou rode: python app.py).");
  }
  window.dispatchEvent(new Event("servidor-online"));
  if (resp.status === 204) return null;
  const dados = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(dados.erro || `Erro ${resp.status}`);
  return dados;
}

const api = {
  listar: (recurso, params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return requisicao("GET", `/${recurso}${qs ? "?" + qs : ""}`);
  },
  criar: (recurso, dados) => requisicao("POST", `/${recurso}`, dados),
  atualizar: (recurso, id, dados) => requisicao("PUT", `/${recurso}/${id}`, dados),
  excluir: (recurso, id) => requisicao("DELETE", `/${recurso}/${id}`),
  resumo: (mes) => requisicao("GET", `/resumo?mes=${mes}`),
  plano: (mes) => requisicao("GET", `/objetivos/plano?mes=${mes}`),
  sugestoes: (mes) => requisicao("GET", `/sugestoes?mes=${mes}`),
  pagamentos: (id) => requisicao("GET", `/parcelamentos/${id}/pagamentos`),
  salvarPagamentos: (id, pagamentos) => requisicao("PUT", `/parcelamentos/${id}/pagamentos`, { pagamentos }),
  fluxo: (mes) => requisicao("GET", `/fluxo?mes=${mes}`),
  projecao: (mes, meses = 6) => requisicao("GET", `/projecao?mes=${mes}&meses=${meses}`),
  simular: (dados) => requisicao("POST", "/simular", dados),
  config: () => requisicao("GET", "/config"),
  salvarConfig: (dados) => requisicao("PUT", "/config", dados),
};
