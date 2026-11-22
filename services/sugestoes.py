"""Regras simples e explicáveis de sugestões para reduzir gastos."""
from services.objetivos import meses_para_juntar

PERCENTUAL_CORTE = 0.20  # simula cortar 20% de uma categoria
LIMITE_CRESCIMENTO = 0.25  # alerta quando a categoria cresce mais de 25%


def _brl(valor):
    s = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def gerar_sugestoes(resumo, medias_anteriores=None, aporte_metas=0.0, falta_metas=0.0,
                    parcelamentos=None, fluxo=None):
    """
    resumo: saída de resumo_mes.
    medias_anteriores: {nome_categoria: média de gasto dos 3 meses anteriores}.
    aporte_metas / falta_metas: usados para mostrar o impacto do corte nas metas.
    """
    medias_anteriores = medias_anteriores or {}
    renda = resumo["renda"]
    saldo = resumo["saldo"]
    sugestoes = []

    if renda <= 0 and resumo["gastos"] <= 0:
        return [
            {
                "tipo": "info",
                "titulo": "Comece cadastrando sua renda e suas contas",
                "texto": "Com renda e gastos cadastrados eu consigo analisar onde dá para economizar.",
            }
        ]

    # 1. Saldo negativo
    if saldo < 0:
        sugestoes.append(
            {
                "tipo": "alerta",
                "titulo": "Você está no vermelho este mês",
                "texto": f"Seus gastos passam a renda em {_brl(-saldo)}. "
                f"É preciso cortar pelo menos esse valor para não ficar devendo.",
                "economia": round(-saldo, 2),
            }
        )

    # 2. Regra 50/30/20
    if renda > 0:
        pct_ess = resumo["essenciais"] / renda
        pct_nao = resumo["nao_essenciais"] / renda
        pct_pou = max(saldo, 0) / renda
        if pct_ess > 0.5:
            sugestoes.append(
                {
                    "tipo": "dica",
                    "titulo": f"Gastos essenciais em {pct_ess:.0%} da renda",
                    "texto": "A regra 50/30/20 recomenda no máximo 50% em essenciais "
                    f"({_brl(renda * 0.5)}). Vale renegociar contas fixas como aluguel, "
                    "plano de celular/internet, seguros e planos.",
                }
            )
        if pct_nao > 0.3:
            excesso = resumo["nao_essenciais"] - renda * 0.3
            sugestoes.append(
                {
                    "tipo": "dica",
                    "titulo": f"Gastos não essenciais em {pct_nao:.0%} da renda",
                    "texto": f"O ideal é até 30% ({_brl(renda * 0.3)}). "
                    f"Reduzir {_brl(excesso)} colocaria você dentro da meta.",
                    "economia": round(excesso, 2),
                }
            )
        if saldo >= 0 and pct_pou < 0.2:
            sugestoes.append(
                {
                    "tipo": "dica",
                    "titulo": f"Você está guardando {pct_pou:.0%} da renda",
                    "texto": f"O recomendado é guardar ao menos 20% ({_brl(renda * 0.2)}/mês) "
                    "para metas e reserva de emergência.",
                }
            )

    # 3. Maiores categorias não essenciais: impacto de cortar 20%
    nao_essenciais = [c for c in resumo["por_categoria"] if not c["essencial"] and c["valor"] > 0]
    for c in nao_essenciais[:3]:
        economia = round(c["valor"] * PERCENTUAL_CORTE, 2)
        texto = f"Cortando 20% em {c['nome']} ({_brl(c['valor'])}/mês) você economiza {_brl(economia)}/mês."
        if falta_metas > 0:
            antes = meses_para_juntar(falta_metas, aporte_metas)
            depois = meses_para_juntar(falta_metas, aporte_metas + economia)
            if antes is None and depois is not None:
                texto += f" Isso já permitiria juntar suas metas em {depois} meses."
            elif antes is not None and depois is not None and antes - depois > 0:
                texto += f" Suas metas ficariam prontas {antes - depois} mês(es) antes."
        sugestoes.append(
            {"tipo": "dica", "titulo": f"Reduzir {c['nome']}", "texto": texto, "economia": economia}
        )

    # 4. Categorias que cresceram em relação à média
    for c in resumo["por_categoria"]:
        media = medias_anteriores.get(c["nome"], 0)
        if media > 0 and c["valor"] > media * (1 + LIMITE_CRESCIMENTO):
            aumento = (c["valor"] / media) - 1
            sugestoes.append(
                {
                    "tipo": "alerta",
                    "titulo": f"{c['nome']} subiu {aumento:.0%}",
                    "texto": f"Este mês: {_brl(c['valor'])}; média dos 3 meses anteriores: {_brl(media)}.",
                    "economia": round(c["valor"] - media, 2),
                }
            )

    # 5. Parcelas e dívidas
    parcelamentos = parcelamentos or []
    total_parcelas = resumo.get("parcelas", 0)
    if renda > 0 and total_parcelas > renda * 0.3:
        sugestoes.append(
            {
                "tipo": "alerta",
                "titulo": f"Parcelas comprometem {total_parcelas / renda:.0%} da renda",
                "texto": f"São {_brl(total_parcelas)} em parcelas este mês. Acima de 30% da renda o risco "
                "de endividamento é alto: evite novas compras parceladas até algumas terminarem.",
            }
        )
    com_juros = [p for p in parcelamentos if p["status"] != "quitado" and p["juros"] > 0]
    if com_juros:
        maior = max(com_juros, key=lambda p: p["juros"])
        sugestoes.append(
            {
                "tipo": "dica",
                "titulo": f"Juros em {maior['descricao']}: {_brl(maior['juros'])}",
                "texto": "Se sobrar dinheiro, priorize antecipar as parcelas com juros (peça desconto "
                "pela antecipação) antes de investir.",
            }
        )
    atrasadas = [p for p in parcelamentos if p.get("parcelas_atrasadas")]
    if atrasadas:
        total = sum(p["valor_atrasado"] for p in atrasadas)
        nomes = ", ".join(f"{p['descricao']} ({p['parcelas_atrasadas']})" for p in atrasadas)
        sugestoes.insert(0, {
            "tipo": "alerta",
            "titulo": f"Parcelas atrasadas: {_brl(total)}",
            "texto": f"Não marcadas como pagas depois do vencimento: {nomes}. Atraso gera juros e multa; "
            "se já pagou, marque em Fixos → Parcelamentos → botão de pagamentos.",
            "economia": None,
        })
    terminando = [p for p in parcelamentos if p["status"] == "ativo" and p.get("meses_restantes", 99) <= 1]
    if terminando:
        livre = sum(p["valor_parcela"] for p in terminando)
        nomes = ", ".join(p["descricao"] for p in terminando)
        sugestoes.append(
            {
                "tipo": "info",
                "titulo": f"{_brl(livre)}/mês livres em breve",
                "texto": f"Terminam nos próximos meses: {nomes}. Quando acabar, direcione esse valor "
                "para suas metas em vez de assumir novas parcelas.",
            }
        )

    # 6. Contas vencendo antes do dinheiro entrar
    renda_sem_dia = fluxo and any(e["valor"] > 0 for e in fluxo.get("sem_dia", []))
    if fluxo and renda_sem_dia:
        sugestoes.append({
            "tipo": "info",
            "titulo": "Informe o dia em que você recebe",
            "texto": "Com o dia de recebimento da renda e o vencimento das contas, eu mostro em quais dias "
            "do mês vai faltar dinheiro (Painel → Fluxo do mês).",
        })
    elif fluxo and fluxo.get("periodos_negativos") and saldo >= 0:
        per = fluxo["periodos_negativos"][0]
        sugestoes.append({
            "tipo": "dica",
            "titulo": f"Falta dinheiro do dia {per['de']} ao dia {per['ate']}",
            "texto": f"No mês fecha positivo, mas algumas contas vencem antes do salário (saldo chega a "
            f"{_brl(fluxo['menor_saldo'])} no dia {fluxo['dia_menor_saldo']}). Deixe {_brl(-fluxo['menor_saldo'])} "
            "guardado para isso ou peça para mudar o vencimento para depois do dia que você recebe.",
        })

    # 7. Assinaturas
    assin = next((c for c in resumo["por_categoria"] if c["nome"] == "Assinaturas"), None)
    if assin and assin["valor"] > 0:
        sugestoes.append(
            {
                "tipo": "info",
                "titulo": f"Assinaturas somam {_brl(assin['valor'])}/mês",
                "texto": f"São {_brl(assin['valor'] * 12)} por ano. Revise streaming, apps e "
                "serviços que você quase não usa.",
            }
        )

    if not sugestoes:
        sugestoes.append(
            {
                "tipo": "ok",
                "titulo": "Suas finanças estão equilibradas",
                "texto": "Continue registrando os gastos e direcionando a sobra para suas metas.",
            }
        )
    return sugestoes
