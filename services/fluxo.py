"""Fluxo de caixa do mês, dia a dia: quando o dinheiro entra e quando as contas vencem."""
import calendar

from services.parcelas import carregar_pagamentos, data_no_mes


def _evento(dia, descricao, valor, tipo, **extra):
    return {"dia": dia, "descricao": descricao, "valor": round(valor, 2), "tipo": tipo, **extra}


def eventos_do_mes(conn, mes):
    ano, m = map(int, mes.split("-"))
    ultimo = calendar.monthrange(ano, m)[1]
    dia_ok = lambda d: min(int(d), ultimo) if d else None  # noqa: E731
    eventos = []

    # Renda fixa (pode ser dividida em 2 datas, ex.: adiantamento dia 20 e restante dia 5)
    for r in conn.execute("SELECT * FROM receitas_fixas WHERE ativo = 1"):
        v2 = r["valor_2"] or 0
        if v2 > 0 and r["dia_recebimento_2"]:
            eventos.append(_evento(dia_ok(r["dia_recebimento"]), r["descricao"], r["valor"] - v2, "receita", parte="1º pagamento"))
            eventos.append(_evento(dia_ok(r["dia_recebimento_2"]), r["descricao"], v2, "receita", parte="2º pagamento"))
        else:
            eventos.append(_evento(dia_ok(r["dia_recebimento"]), r["descricao"], r["valor"], "receita"))

    for d in conn.execute("SELECT * FROM despesas_fixas WHERE ativo = 1"):
        eventos.append(_evento(dia_ok(d["dia_vencimento"]), d["descricao"], -d["valor"], "conta"))

    for l in conn.execute("SELECT * FROM lancamentos WHERE substr(data, 1, 7) = ?", (mes,)):
        sinal = 1 if l["tipo"] == "receita" else -1
        eventos.append(_evento(int(l["data"][8:10]), l["descricao"], sinal * l["valor"],
                               "receita" if sinal > 0 else "avulso"))

    pags = carregar_pagamentos(conn)
    idx = ano * 12 + m - 1
    for p in conn.execute("SELECT * FROM parcelamentos"):
        a, mm = map(int, p["primeira_parcela"].split("-"))
        numero = idx - (a * 12 + mm - 1) + 1
        if 1 <= numero <= p["num_parcelas"]:
            pago_em = pags.get(p["id"], {}).get(numero)
            eventos.append(_evento(dia_ok(p["dia_vencimento"]), p["descricao"], -p["valor_parcela"], "parcela",
                                   parcela=f"{numero}/{p['num_parcelas']}", pago_em=pago_em))
    return eventos, ultimo


def fluxo_mes(conn, mes):
    eventos, ultimo = eventos_do_mes(conn, mes)
    com_dia = sorted((e for e in eventos if e["dia"]), key=lambda e: (e["dia"], -e["valor"]))
    sem_dia = [e for e in eventos if not e["dia"]]

    saldo = 0.0
    for e in com_dia:
        saldo += e["valor"]
        e["saldo_apos"] = round(saldo, 2)
        e["data"] = data_no_mes(mes, e["dia"])

    # saldo ao fim de cada dia (para o gráfico) e períodos no negativo
    dias, i, saldo = [], 0, 0.0
    menor, dia_menor = 0.0, None
    periodos, inicio = [], None
    for dia in range(1, ultimo + 1):
        while i < len(com_dia) and com_dia[i]["dia"] == dia:
            saldo += com_dia[i]["valor"]
            i += 1
        saldo_r = round(saldo, 2)
        dias.append({"dia": dia, "saldo": saldo_r})
        if saldo_r < menor:
            menor, dia_menor = saldo_r, dia
        if saldo_r < 0 and inicio is None:
            inicio = dia
        elif saldo_r >= 0 and inicio is not None:
            periodos.append({"de": inicio, "ate": dia - 1})
            inicio = None
    if inicio is not None:
        periodos.append({"de": inicio, "ate": ultimo})

    total_sem_dia = round(sum(e["valor"] for e in sem_dia), 2)
    return {
        "mes": mes,
        "eventos": com_dia,
        "sem_dia": sem_dia,
        "dias": dias,
        "saldo_dias_definidos": round(saldo, 2),
        "total_sem_dia": total_sem_dia,
        "saldo_final": round(saldo + total_sem_dia, 2),
        "menor_saldo": menor,
        "dia_menor_saldo": dia_menor,
        "periodos_negativos": periodos,
        "entradas": round(sum(e["valor"] for e in eventos if e["valor"] > 0), 2),
        "saidas": round(-sum(e["valor"] for e in eventos if e["valor"] < 0), 2),
    }
