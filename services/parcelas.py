"""Compras parceladas e dívidas: parcelas pagas, vencimentos, atrasos e quanto falta."""
import calendar
from datetime import date

from services.resumo import deslocar_mes, indice_mes


def valor_parcela_padrao(valor_total, num_parcelas):
    return round(float(valor_total) / int(num_parcelas), 2)


def data_no_mes(mes, dia):
    """Data AAAA-MM-DD do dia `dia` no mês; dia 31 em fevereiro vira o último dia do mês."""
    ano, m = map(int, mes.split("-"))
    ultimo = calendar.monthrange(ano, m)[1]
    return f"{mes}-{min(int(dia), ultimo):02d}"


def vencimento(p, numero):
    """Data de vencimento da parcela `numero` (1..n). Sem dia definido: último dia do mês."""
    mes = deslocar_mes(p["primeira_parcela"], numero - 1)
    return data_no_mes(mes, p.get("dia_vencimento") or 31)


def detalhar(p, mes, pagamentos=None, hoje=None):
    """
    Situação do parcelamento `p` no mês `mes` (AAAA-MM).
    pagamentos: {numero_da_parcela: 'AAAA-MM-DD'} das parcelas já pagas.
    """
    pagamentos = pagamentos or {}
    hoje = hoje or date.today().isoformat()
    n = int(p["num_parcelas"])
    parcela = float(p["valor_parcela"])
    diff = indice_mes(mes) - indice_mes(p["primeira_parcela"])

    if diff < 0:
        status, parcela_atual = "futuro", None
    elif diff >= n:
        status, parcela_atual = "quitado", None
    else:
        status, parcela_atual = "ativo", diff + 1

    pagas = sorted(k for k in pagamentos if 1 <= k <= n)
    nao_pagas = [k for k in range(1, n + 1) if k not in pagamentos]
    atrasadas = [k for k in nao_pagas if vencimento(p, k) < hoje]
    proxima = nao_pagas[0] if nao_pagas else None
    total_a_pagar = round(parcela * n, 2)
    ultimo_pagamento = max(pagamentos.values()) if pagamentos else None

    return {
        **p,
        "status": status,
        "parcela_atual": parcela_atual,
        "parcela_atual_paga": parcela_atual in pagamentos if parcela_atual else None,
        "vencimento_no_mes": vencimento(p, parcela_atual) if parcela_atual else None,
        "meses_restantes": max(n - max(diff + 1, 0), 0),  # pelo calendário, depois deste mês
        "parcelas_pagas": len(pagas),
        "parcelas_restantes": n - len(pagas),
        "parcelas_atrasadas": len(atrasadas),
        "valor_atrasado": round(parcela * len(atrasadas), 2),
        "proxima_parcela": proxima,
        "proximo_vencimento": vencimento(p, proxima) if proxima else None,
        "ultimo_pagamento": ultimo_pagamento,
        "valor_no_mes": parcela if status == "ativo" else 0.0,
        "valor_restante": round(parcela * (n - len(pagas)), 2),
        "total_a_pagar": total_a_pagar,
        "juros": round(max(total_a_pagar - float(p["valor_total"]), 0), 2),
        "ultima_parcela": deslocar_mes(p["primeira_parcela"], n - 1),
        "progresso": round(len(pagas) / n * 100, 1),
    }


def carregar_pagamentos(conn, parcelamento_id=None):
    """{parcelamento_id: {numero: data}}"""
    sql = "SELECT parcelamento_id, numero, data_pagamento FROM pagamentos_parcela"
    params = ()
    if parcelamento_id is not None:
        sql += " WHERE parcelamento_id = ?"
        params = (parcelamento_id,)
    resultado = {}
    for r in conn.execute(sql, params):
        resultado.setdefault(r["parcelamento_id"], {})[r["numero"]] = r["data_pagamento"]
    return resultado


def listar_detalhados(conn, mes, hoje=None):
    pags = carregar_pagamentos(conn)
    rows = conn.execute("SELECT * FROM parcelamentos ORDER BY primeira_parcela, id").fetchall()
    return [detalhar(dict(r), mes, pags.get(r["id"], {}), hoje) for r in rows]
