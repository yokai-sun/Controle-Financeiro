"""Cálculos de objetivos/metas: quanto guardar por mês e em quantos meses."""
import math
from datetime import date

from services.resumo import deslocar_mes


def meses_para_juntar(falta, aporte_mensal):
    """Quantos meses para juntar `falta` guardando `aporte_mensal`. None se impossível."""
    if falta <= 0:
        return 0
    if not aporte_mensal or aporte_mensal <= 0:
        return None
    return math.ceil(round(falta / aporte_mensal, 6))


def _mes_conclusao(meses, mes_base):
    if meses is None:
        return None
    return deslocar_mes(mes_base, meses)


def plano_objetivos(objetivos, sobra_mensal, percentual_metas=100.0, mes_base=None):
    """
    objetivos: lista de dicts com nome, valor_alvo, valor_guardado, prazo_meses, prioridade.
    sobra_mensal: renda - gastos do mês.
    A sobra destinada às metas é aplicada em sequência, por prioridade (1 = mais importante).
    """
    mes_base = mes_base or date.today().strftime("%Y-%m")
    aporte = max(sobra_mensal, 0) * (percentual_metas / 100.0)
    ordenados = sorted(objetivos, key=lambda o: (o.get("prioridade") or 99, o.get("id") or 0))

    itens = []
    acumulado = 0.0
    soma_mensal_prazo = 0.0
    for o in ordenados:
        alvo = float(o["valor_alvo"])
        guardado = float(o.get("valor_guardado") or 0)
        falta = max(alvo - guardado, 0)
        prazo = o.get("prazo_meses")
        mensal_necessario = round(falta / prazo, 2) if prazo else None
        if mensal_necessario:
            soma_mensal_prazo += mensal_necessario

        meses_sozinho = meses_para_juntar(falta, aporte)
        acumulado += falta
        meses_seq = meses_para_juntar(acumulado, aporte)

        itens.append(
            {
                **o,
                "falta": round(falta, 2),
                "progresso": round(guardado / alvo * 100, 1) if alvo > 0 else 100.0,
                "mensal_necessario": mensal_necessario,
                "viavel_no_prazo": (mensal_necessario <= aporte + 0.005)
                if mensal_necessario is not None
                else None,
                "meses_se_unico": meses_sozinho,
                "meses_em_sequencia": meses_seq,
                "conclusao_em_sequencia": _mes_conclusao(meses_seq, mes_base),
            }
        )

    falta_total = round(acumulado, 2)
    meses_total = meses_para_juntar(falta_total, aporte)
    return {
        "aporte_mensal": round(aporte, 2),
        "sobra_mensal": round(sobra_mensal, 2),
        "percentual_metas": percentual_metas,
        "falta_total": falta_total,
        "meses_total": meses_total,
        "conclusao_total": _mes_conclusao(meses_total, mes_base),
        "soma_mensal_prazos": round(soma_mensal_prazo, 2),
        "prazos_viaveis": soma_mensal_prazo <= aporte + 0.005,
        "objetivos": itens,
    }


def simular(metas, aporte_mensal=None, prazo_meses=None, ja_guardado=0.0, mes_base=None):
    """
    Simulação livre (não salva nada): ex. viagem X + intercâmbio Y.
    - Com prazo: quanto guardar por mês.
    - Com aporte: em quantos meses junta (e quando cada meta fica pronta, em sequência).
    """
    mes_base = mes_base or date.today().strftime("%Y-%m")
    total = sum(float(m.get("valor") or 0) for m in metas)
    falta = max(total - float(ja_guardado or 0), 0)
    resultado = {"total": round(total, 2), "falta": round(falta, 2)}

    if prazo_meses:
        resultado["mensal_necessario"] = round(falta / int(prazo_meses), 2)
        resultado["prazo_meses"] = int(prazo_meses)
        resultado["conclusao_prazo"] = deslocar_mes(mes_base, int(prazo_meses))

    if aporte_mensal:
        aporte = float(aporte_mensal)
        resultado["aporte_mensal"] = round(aporte, 2)
        resultado["meses"] = meses_para_juntar(falta, aporte)
        resultado["conclusao"] = _mes_conclusao(resultado["meses"], mes_base)
        linha = []
        restante_guardado = float(ja_guardado or 0)
        acumulado = 0.0
        for m in metas:
            valor = float(m.get("valor") or 0)
            usado = min(valor, restante_guardado)
            restante_guardado -= usado
            acumulado += valor - usado
            meses = meses_para_juntar(acumulado, aporte)
            linha.append(
                {
                    "nome": m.get("nome") or "Meta",
                    "valor": round(valor, 2),
                    "meses": meses,
                    "conclusao": _mes_conclusao(meses, mes_base),
                }
            )
        resultado["linha_do_tempo"] = linha
        if prazo_meses:
            resultado["cabe_no_prazo"] = aporte * int(prazo_meses) + 0.005 >= falta

    return resultado
