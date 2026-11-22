"""Cálculo do resumo financeiro de um mês."""
from datetime import date

LIMITE_ATENCAO = 80.0  # % da renda comprometida a partir do qual o status vira "atenção"


def mes_atual():
    return date.today().strftime("%Y-%m")


def indice_mes(mes):
    """'2026-11' -> número sequencial de meses (para comparar/subtrair meses)."""
    ano, m = map(int, mes.split("-"))
    return ano * 12 + (m - 1)


# Parcelas que caem no mês: índice da 1ª parcela <= mês < 1ª parcela + nº de parcelas
SQL_PARCELA_NO_MES = """
    (CAST(substr(primeira_parcela, 1, 4) AS INTEGER) * 12
     + CAST(substr(primeira_parcela, 6, 2) AS INTEGER) - 1) <= :idx
    AND :idx < (CAST(substr(primeira_parcela, 1, 4) AS INTEGER) * 12
     + CAST(substr(primeira_parcela, 6, 2) AS INTEGER) - 1) + num_parcelas
"""


def deslocar_mes(mes, n):
    """'2026-11', -1 -> '2026-10'."""
    ano, m = map(int, mes.split("-"))
    total = ano * 12 + (m - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def calcular_status(renda, gastos):
    """Retorna (percentual_comprometido, status)."""
    saldo = renda - gastos
    if renda <= 0:
        percentual = 100.0 if gastos > 0 else 0.0
    else:
        percentual = round(gastos / renda * 100, 1)
    if saldo < 0:
        status = "vermelho"
    elif percentual > LIMITE_ATENCAO:
        status = "atencao"
    else:
        status = "ok"
    return percentual, status


def _totais_mes(conn, mes):
    renda_fixa = conn.execute(
        "SELECT COALESCE(SUM(valor), 0) FROM receitas_fixas WHERE ativo = 1"
    ).fetchone()[0]
    despesas_fixas = conn.execute(
        "SELECT COALESCE(SUM(valor), 0) FROM despesas_fixas WHERE ativo = 1"
    ).fetchone()[0]
    var = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor END), 0),
             COALESCE(SUM(CASE WHEN tipo = 'despesa' THEN valor END), 0)
           FROM lancamentos WHERE substr(data, 1, 7) = ?""",
        (mes,),
    ).fetchone()
    parcelas = conn.execute(
        f"SELECT COALESCE(SUM(valor_parcela), 0) FROM parcelamentos WHERE {SQL_PARCELA_NO_MES}",
        {"idx": indice_mes(mes)},
    ).fetchone()[0]
    return {
        "renda_fixa": renda_fixa,
        "renda_variavel": var[0],
        "despesas_fixas": despesas_fixas,
        "despesas_variaveis": var[1],
        "parcelas": parcelas,
    }


def _gastos_totais(t):
    return t["despesas_fixas"] + t["despesas_variaveis"] + t["parcelas"]


def gastos_por_categoria(conn, mes):
    rows = conn.execute(
        """SELECT c.id, COALESCE(c.nome, 'Sem categoria') AS nome,
                  COALESCE(c.cor, '#94a3b8') AS cor, COALESCE(c.essencial, 0) AS essencial,
                  SUM(t.valor) AS valor, SUM(t.fixo) AS fixo
           FROM (
               SELECT categoria_id, valor, valor AS fixo FROM despesas_fixas WHERE ativo = 1
               UNION ALL
               SELECT categoria_id, valor, 0 FROM lancamentos
                WHERE tipo = 'despesa' AND substr(data, 1, 7) = :mes
               UNION ALL
               SELECT categoria_id, valor_parcela, valor_parcela FROM parcelamentos
                WHERE {SQL_PARCELA_NO_MES}
           ) t
           LEFT JOIN categorias c ON c.id = t.categoria_id
           GROUP BY c.id
           ORDER BY valor DESC""".replace("{SQL_PARCELA_NO_MES}", SQL_PARCELA_NO_MES),
        {"mes": mes, "idx": indice_mes(mes)},
    ).fetchall()
    return [
        {
            "categoria_id": r["id"],
            "nome": r["nome"],
            "cor": r["cor"],
            "essencial": bool(r["essencial"]),
            "valor": round(r["valor"], 2),
            "fixo": round(r["fixo"], 2),
        }
        for r in rows
    ]


def resumo_mes(conn, mes, com_historico=True):
    t = _totais_mes(conn, mes)
    renda = t["renda_fixa"] + t["renda_variavel"]
    gastos = _gastos_totais(t)
    saldo = renda - gastos
    percentual, status = calcular_status(renda, gastos)
    categorias = gastos_por_categoria(conn, mes)
    essenciais = sum(c["valor"] for c in categorias if c["essencial"])

    resultado = {
        "mes": mes,
        "renda": round(renda, 2),
        "renda_fixa": round(t["renda_fixa"], 2),
        "renda_variavel": round(t["renda_variavel"], 2),
        "gastos": round(gastos, 2),
        "despesas_fixas": round(t["despesas_fixas"], 2),
        "despesas_variaveis": round(t["despesas_variaveis"], 2),
        "parcelas": round(t["parcelas"], 2),
        "saldo": round(saldo, 2),
        "percentual_comprometido": percentual,
        "status": status,
        "essenciais": round(essenciais, 2),
        "nao_essenciais": round(gastos - essenciais, 2),
        "por_categoria": categorias,
    }
    if com_historico:
        historico = []
        for i in range(5, -1, -1):
            m = deslocar_mes(mes, -i)
            tm = _totais_mes(conn, m)
            historico.append(
                {
                    "mes": m,
                    "renda": round(tm["renda_fixa"] + tm["renda_variavel"], 2),
                    "gastos": round(_gastos_totais(tm), 2),
                }
            )
        resultado["historico"] = historico
    return resultado
