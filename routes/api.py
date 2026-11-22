"""API REST JSON (/api/v1). O front web e um futuro app mobile usam esta mesma API."""
import re

from flask import Blueprint, current_app, jsonify, request

from database import conexao, get_config
from services.objetivos import plano_objetivos, simular
from services.fluxo import fluxo_mes
from services.parcelas import carregar_pagamentos, listar_detalhados, valor_parcela_padrao, vencimento
from services.resumo import deslocar_mes, mes_atual, resumo_mes
from services.sugestoes import gerar_sugestoes

api = Blueprint("api", __name__, url_prefix="/api/v1")

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ErroValidacao(Exception):
    pass


@api.errorhandler(ErroValidacao)
def _erro_validacao(e):
    return jsonify({"erro": str(e)}), 400


def conn():
    return conexao(current_app.config.get("DB_PATH"))


def _mes_param():
    mes = request.args.get("mes") or mes_atual()
    if not MES_RE.match(mes):
        raise ErroValidacao("Parâmetro 'mes' deve estar no formato AAAA-MM.")
    return mes


# ---------- conversores de campos ----------
def _texto(v, campo):
    v = (str(v) if v is not None else "").strip()
    if not v:
        raise ErroValidacao(f"O campo '{campo}' é obrigatório.")
    return v[:200]


def _valor(v, campo):
    try:
        n = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        raise ErroValidacao(f"O campo '{campo}' deve ser um número.")
    if n < 0:
        raise ErroValidacao(f"O campo '{campo}' não pode ser negativo.")
    return round(n, 2)


def _inteiro_opcional(v, campo):
    if v in (None, "", 0, "0"):
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ErroValidacao(f"O campo '{campo}' deve ser um número inteiro.")
    if n <= 0:
        raise ErroValidacao(f"O campo '{campo}' deve ser maior que zero.")
    return n


def _bool(v, campo):
    return 1 if v in (True, 1, "1", "true", "on") else 0


def _categoria(v, campo):
    return _inteiro_opcional(v, campo)


def _data(v, campo):
    v = _texto(v, campo)
    if not DATA_RE.match(v):
        raise ErroValidacao(f"O campo '{campo}' deve estar no formato AAAA-MM-DD.")
    return v


def _tipo(v, campo):
    if v not in ("receita", "despesa"):
        raise ErroValidacao("O campo 'tipo' deve ser 'receita' ou 'despesa'.")
    return v


def _valor_opcional(v, campo):
    return None if v in (None, "") else _valor(v, campo)


def _valor_positivo(v, campo):
    n = _valor(v, campo)
    if n <= 0:
        raise ErroValidacao(f"O campo '{campo}' deve ser maior que zero.")
    return n


def _inteiro_obrigatorio(v, campo):
    n = _inteiro_opcional(v, campo)
    if n is None:
        raise ErroValidacao(f"O campo '{campo}' é obrigatório e deve ser maior que zero.")
    if n > 600:
        raise ErroValidacao(f"O campo '{campo}' deve ser no máximo 600.")
    return n


def _dia(v, campo):
    n = _inteiro_opcional(v, campo)
    if n is not None and n > 31:
        raise ErroValidacao(f"O campo '{campo}' deve ser um dia entre 1 e 31.")
    return n


def _pos_receita(dados, parcial):
    """Renda dividida em 2 datas: valor_2 é a parte recebida no 2º dia."""
    v2 = dados.get("valor_2") or 0
    if v2 > 0:
        if not dados.get("dia_recebimento_2"):
            raise ErroValidacao("Informe o dia do 2º pagamento.")
        if "valor" in dados and v2 >= dados["valor"]:
            raise ErroValidacao("O 2º pagamento deve ser menor que o valor total.")
    elif "valor_2" in dados:
        dados["dia_recebimento_2"] = None
    return dados


def _mes(v, campo):
    v = _texto(v, campo)
    if not MES_RE.match(v):
        raise ErroValidacao(f"O campo '{campo}' deve estar no formato AAAA-MM.")
    return v


def _tipo_parcelamento(v, campo):
    if v not in ("compra", "divida"):
        raise ErroValidacao("O campo 'tipo' deve ser 'compra' ou 'divida'.")
    return v


def _pos_parcelamento(dados, parcial):
    """Sem valor da parcela informado: divide o total pelo número de parcelas."""
    if dados.get("valor_parcela") is None and ("valor_parcela" in dados or not parcial):
        if "valor_total" not in dados or "num_parcelas" not in dados:
            raise ErroValidacao("Informe o valor total e o número de parcelas.")
        dados["valor_parcela"] = valor_parcela_padrao(dados["valor_total"], dados["num_parcelas"])
    return dados


def _cor(v, campo):
    v = (v or "#64748b").strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", v):
        raise ErroValidacao("Cor inválida (use #RRGGBB).")
    return v


# tabela -> {campo: (conversor, obrigatório, padrão)}
RECURSOS = {
    "categorias": {
        "tabela": "categorias",
        "campos": {
            "nome": (_texto, True, None),
            "cor": (_cor, False, "#64748b"),
            "essencial": (_bool, False, 0),
        },
        "ordem": "nome",
    },
    "receitas-fixas": {
        "tabela": "receitas_fixas",
        "campos": {
            "descricao": (_texto, True, None),
            "valor": (_valor, True, None),
            "dia_recebimento": (_dia, False, None),
            "valor_2": (_valor, False, 0),
            "dia_recebimento_2": (_dia, False, None),
            "ativo": (_bool, False, 1),
        },
        "ordem": "valor DESC",
        "pos": _pos_receita,
    },
    "despesas-fixas": {
        "tabela": "despesas_fixas",
        "campos": {
            "descricao": (_texto, True, None),
            "valor": (_valor, True, None),
            "categoria_id": (_categoria, False, None),
            "dia_vencimento": (_inteiro_opcional, False, None),
            "ativo": (_bool, False, 1),
        },
        "ordem": "valor DESC",
    },
    "lancamentos": {
        "tabela": "lancamentos",
        "campos": {
            "data": (_data, True, None),
            "descricao": (_texto, True, None),
            "valor": (_valor, True, None),
            "tipo": (_tipo, True, None),
            "categoria_id": (_categoria, False, None),
        },
        "ordem": "data DESC, id DESC",
    },
    "parcelamentos": {
        "tabela": "parcelamentos",
        "campos": {
            "descricao": (_texto, True, None),
            "tipo": (_tipo_parcelamento, False, "compra"),
            "valor_total": (_valor_positivo, True, None),
            "num_parcelas": (_inteiro_obrigatorio, True, None),
            "valor_parcela": (_valor_opcional, False, None),
            "primeira_parcela": (_mes, True, None),
            "dia_vencimento": (_dia, False, None),
            "categoria_id": (_categoria, False, None),
        },
        "ordem": "primeira_parcela, id",
        "pos": _pos_parcelamento,
    },
    "objetivos": {
        "tabela": "objetivos",
        "campos": {
            "nome": (_texto, True, None),
            "valor_alvo": (_valor, True, None),
            "valor_guardado": (_valor, False, 0),
            "prazo_meses": (_inteiro_opcional, False, None),
            "prioridade": (_inteiro_opcional, False, 1),
            "icone": (lambda v, c: (v or "🎯")[:4], False, "🎯"),
        },
        "ordem": "prioridade, id",
    },
}


def _validar(spec, dados, parcial=False):
    limpo = {}
    for campo, (conv, obrigatorio, padrao) in spec["campos"].items():
        if campo in dados:
            limpo[campo] = conv(dados[campo], campo)
        elif not parcial:
            if obrigatorio:
                raise ErroValidacao(f"O campo '{campo}' é obrigatório.")
            limpo[campo] = padrao
    if "prioridade" in limpo and limpo["prioridade"] is None:
        limpo["prioridade"] = 1
    if "pos" in spec:
        limpo = spec["pos"](limpo, parcial)
    return limpo


def _dict(row):
    return dict(row) if row else None


def _listar(nome):
    spec = RECURSOS[nome]
    sql = f"SELECT * FROM {spec['tabela']}"
    params = []
    if nome == "lancamentos":
        sql += " WHERE substr(data, 1, 7) = ?"
        params.append(_mes_param())
    sql += f" ORDER BY {spec['ordem']}"
    with conn() as c:
        if nome == "parcelamentos":
            return listar_detalhados(c, _mes_param())
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def _registrar_crud(nome):
    spec = RECURSOS[nome]
    tabela = spec["tabela"]
    endpoint = nome.replace("-", "_")

    def listar():
        return jsonify(_listar(nome))

    def criar():
        dados = _validar(spec, request.get_json(silent=True) or {})
        cols = ", ".join(dados)
        marks = ", ".join("?" for _ in dados)
        with conn() as c:
            cur = c.execute(f"INSERT INTO {tabela} ({cols}) VALUES ({marks})", list(dados.values()))
            row = c.execute(f"SELECT * FROM {tabela} WHERE id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(_dict(row)), 201

    def obter(item_id):
        with conn() as c:
            row = c.execute(f"SELECT * FROM {tabela} WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return jsonify({"erro": "Não encontrado."}), 404
        return jsonify(_dict(row))

    def atualizar(item_id):
        dados = _validar(spec, request.get_json(silent=True) or {}, parcial=True)
        if not dados:
            raise ErroValidacao("Nenhum campo para atualizar.")
        sets = ", ".join(f"{k} = ?" for k in dados)
        with conn() as c:
            cur = c.execute(
                f"UPDATE {tabela} SET {sets} WHERE id = ?", [*dados.values(), item_id]
            )
            if cur.rowcount == 0:
                return jsonify({"erro": "Não encontrado."}), 404
            row = c.execute(f"SELECT * FROM {tabela} WHERE id = ?", (item_id,)).fetchone()
        return jsonify(_dict(row))

    def excluir(item_id):
        with conn() as c:
            cur = c.execute(f"DELETE FROM {tabela} WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            return jsonify({"erro": "Não encontrado."}), 404
        return "", 204

    api.add_url_rule(f"/{nome}", f"{endpoint}_listar", listar, methods=["GET"])
    api.add_url_rule(f"/{nome}", f"{endpoint}_criar", criar, methods=["POST"])
    api.add_url_rule(f"/{nome}/<int:item_id>", f"{endpoint}_obter", obter, methods=["GET"])
    api.add_url_rule(f"/{nome}/<int:item_id>", f"{endpoint}_atualizar", atualizar, methods=["PUT"])
    api.add_url_rule(f"/{nome}/<int:item_id>", f"{endpoint}_excluir", excluir, methods=["DELETE"])


for _nome in RECURSOS:
    _registrar_crud(_nome)


# ---------- endpoints calculados ----------
def _plano(c, mes):
    resumo = resumo_mes(c, mes, com_historico=False)
    objetivos = [dict(r) for r in c.execute("SELECT * FROM objetivos").fetchall()]
    pct = float(get_config(c, "percentual_metas", "100"))
    return resumo, plano_objetivos(objetivos, resumo["saldo"], pct, mes_base=mes)


@api.get("/resumo")
def resumo():
    with conn() as c:
        return jsonify(resumo_mes(c, _mes_param()))


@api.get("/objetivos/plano")
def objetivos_plano():
    with conn() as c:
        _, plano = _plano(c, _mes_param())
    return jsonify(plano)


@api.post("/simular")
def simular_metas():
    dados = request.get_json(silent=True) or {}
    metas = dados.get("metas") or []
    if not isinstance(metas, list) or not metas:
        raise ErroValidacao("Informe ao menos uma meta.")
    metas = [{"nome": str(m.get("nome") or "Meta")[:60], "valor": _valor(m.get("valor"), "valor")}
             for m in metas]
    aporte = dados.get("aporte_mensal")
    aporte = _valor(aporte, "aporte_mensal") if aporte not in (None, "") else None
    prazo = _inteiro_opcional(dados.get("prazo_meses"), "prazo_meses")
    guardado = dados.get("ja_guardado")
    guardado = _valor(guardado, "ja_guardado") if guardado not in (None, "") else 0
    if not aporte and not prazo:
        raise ErroValidacao("Informe o valor que pode guardar por mês ou o prazo em meses.")
    return jsonify(simular(metas, aporte, prazo, guardado, mes_base=mes_atual()))


@api.get("/parcelamentos/<int:item_id>/pagamentos")
def listar_pagamentos(item_id):
    """Todas as parcelas do parcelamento, com vencimento e se/quando foi paga."""
    with conn() as c:
        row = c.execute("SELECT * FROM parcelamentos WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return jsonify({"erro": "Não encontrado."}), 404
        p = dict(row)
        pagos = carregar_pagamentos(c, item_id).get(item_id, {})
    return jsonify([
        {
            "numero": k,
            "mes": deslocar_mes(p["primeira_parcela"], k - 1),
            "vencimento": vencimento(p, k),
            "valor": p["valor_parcela"],
            "pago": k in pagos,
            "data_pagamento": pagos.get(k),
        }
        for k in range(1, p["num_parcelas"] + 1)
    ])


@api.put("/parcelamentos/<int:item_id>/pagamentos")
def salvar_pagamentos(item_id):
    """Substitui a lista de parcelas pagas: {pagamentos: [{numero, data_pagamento}]}"""
    dados = request.get_json(silent=True) or {}
    lista = dados.get("pagamentos")
    if not isinstance(lista, list):
        raise ErroValidacao("Envie a lista 'pagamentos'.")
    with conn() as c:
        row = c.execute("SELECT num_parcelas FROM parcelamentos WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return jsonify({"erro": "Não encontrado."}), 404
        registros = {}
        for item in lista:
            numero = _inteiro_obrigatorio(item.get("numero"), "numero")
            if numero > row["num_parcelas"]:
                raise ErroValidacao(f"A parcela {numero} não existe (são {row['num_parcelas']}).")
            registros[numero] = _data(item.get("data_pagamento"), "data_pagamento")
        c.execute("DELETE FROM pagamentos_parcela WHERE parcelamento_id = ?", (item_id,))
        c.executemany(
            "INSERT INTO pagamentos_parcela (parcelamento_id, numero, data_pagamento) VALUES (?, ?, ?)",
            [(item_id, k, d) for k, d in registros.items()],
        )
    return jsonify({"pagas": len(registros)})


@api.get("/fluxo")
def fluxo():
    with conn() as c:
        return jsonify(fluxo_mes(c, _mes_param()))


@api.get("/projecao")
def projecao():
    """Quanto sobra ou falta nos próximos meses (renda e contas fixas + parcelas;
    gastos avulsos só entram nos meses em que já foram lançados)."""
    mes = _mes_param()
    try:
        n = min(max(int(request.args.get("meses", 6)), 1), 24)
    except ValueError:
        raise ErroValidacao("Parâmetro 'meses' inválido.")
    with conn() as c:
        itens = []
        for i in range(n):
            r = resumo_mes(c, deslocar_mes(mes, i), com_historico=False)
            itens.append({k: r[k] for k in ("mes", "renda", "gastos", "parcelas", "saldo", "status")})
    return jsonify(itens)


@api.get("/sugestoes")
def sugestoes():
    mes = _mes_param()
    with conn() as c:
        resumo, plano = _plano(c, mes)
        soma = {}
        for i in range(1, 4):
            for cat in resumo_mes(c, deslocar_mes(mes, -i), com_historico=False)["por_categoria"]:
                soma[cat["nome"]] = soma.get(cat["nome"], 0) + cat["valor"]
        parcelamentos = listar_detalhados(c, mes)
        fluxo_m = fluxo_mes(c, mes)
    medias = {k: v / 3 for k, v in soma.items()}
    return jsonify(gerar_sugestoes(resumo, medias, plano["aporte_mensal"], plano["falta_total"],
                                   parcelamentos, fluxo_m))


@api.get("/config")
def obter_config():
    with conn() as c:
        return jsonify({r["chave"]: r["valor"] for r in c.execute("SELECT * FROM config")})


@api.put("/config")
def salvar_config():
    dados = request.get_json(silent=True) or {}
    with conn() as c:
        if "percentual_metas" in dados:
            pct = _valor(dados["percentual_metas"], "percentual_metas")
            if pct > 100:
                raise ErroValidacao("O percentual deve ser entre 0 e 100.")
            c.execute(
                "INSERT OR REPLACE INTO config (chave, valor) VALUES ('percentual_metas', ?)",
                (str(pct),),
            )
        return jsonify({r["chave"]: r["valor"] for r in c.execute("SELECT * FROM config")})
