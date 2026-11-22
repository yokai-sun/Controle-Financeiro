"""Testes dos cálculos e da API.  Rode com:  python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from services.objetivos import meses_para_juntar, plano_objetivos, simular  # noqa: E402
from services.resumo import calcular_status, deslocar_mes  # noqa: E402
from services.sugestoes import gerar_sugestoes  # noqa: E402


class TestCalculos(unittest.TestCase):
    def test_deslocar_mes(self):
        self.assertEqual(deslocar_mes("2026-01", -1), "2025-12")
        self.assertEqual(deslocar_mes("2026-11", 14), "2028-01")

    def test_status(self):
        self.assertEqual(calcular_status(5000, 3000), (60.0, "ok"))
        self.assertEqual(calcular_status(5000, 4500)[1], "atencao")
        self.assertEqual(calcular_status(5000, 5500)[1], "vermelho")
        self.assertEqual(calcular_status(0, 0), (0.0, "ok"))

    def test_meses_para_juntar(self):
        self.assertEqual(meses_para_juntar(28000, 1500), 19)  # 18,67 -> 19
        self.assertEqual(meses_para_juntar(3000, 1000), 3)
        self.assertEqual(meses_para_juntar(0, 0), 0)
        self.assertIsNone(meses_para_juntar(1000, 0))

    def test_simular_viagem_e_intercambio(self):
        metas = [{"nome": "Viagem", "valor": 8000}, {"nome": "Intercâmbio", "valor": 20000}]
        r = simular(metas, aporte_mensal=1500, prazo_meses=12, mes_base="2026-11")
        self.assertEqual(r["total"], 28000)
        self.assertAlmostEqual(r["mensal_necessario"], 2333.33)
        self.assertEqual(r["meses"], 19)
        self.assertEqual(r["conclusao"], "2028-06")
        self.assertFalse(r["cabe_no_prazo"])
        self.assertEqual([m["meses"] for m in r["linha_do_tempo"]], [6, 19])

    def test_simular_com_valor_guardado(self):
        r = simular([{"nome": "A", "valor": 5000}, {"nome": "B", "valor": 5000}], aporte_mensal=1000,
                    ja_guardado=6000, mes_base="2026-01")
        self.assertEqual(r["falta"], 4000)
        self.assertEqual([m["meses"] for m in r["linha_do_tempo"]], [0, 4])

    def test_plano_por_prioridade(self):
        objs = [
            {"id": 1, "nome": "Intercâmbio", "valor_alvo": 20000, "valor_guardado": 0, "prazo_meses": None, "prioridade": 2},
            {"id": 2, "nome": "Viagem", "valor_alvo": 8000, "valor_guardado": 2000, "prazo_meses": 6, "prioridade": 1},
        ]
        p = plano_objetivos(objs, sobra_mensal=2000, percentual_metas=50, mes_base="2026-11")
        self.assertEqual(p["aporte_mensal"], 1000)
        self.assertEqual(p["falta_total"], 26000)
        viagem, inter = p["objetivos"]
        self.assertEqual(viagem["nome"], "Viagem")
        self.assertEqual(viagem["mensal_necessario"], 1000)
        self.assertTrue(viagem["viavel_no_prazo"])
        self.assertEqual(viagem["meses_em_sequencia"], 6)
        self.assertEqual(inter["meses_em_sequencia"], 26)

    def test_plano_sem_sobra(self):
        p = plano_objetivos([{"nome": "Carro", "valor_alvo": 50000}], sobra_mensal=-300)
        self.assertEqual(p["aporte_mensal"], 0)
        self.assertIsNone(p["meses_total"])

    def test_sugestoes_vermelho_e_corte(self):
        resumo = {
            "renda": 3000, "gastos": 3500, "saldo": -500, "essenciais": 2000, "nao_essenciais": 1500,
            "por_categoria": [
                {"nome": "Moradia", "valor": 2000, "essencial": True},
                {"nome": "Lazer", "valor": 1000, "essencial": False},
                {"nome": "Assinaturas", "valor": 500, "essencial": False},
            ],
        }
        s = gerar_sugestoes(resumo, {"Lazer": 500})
        titulos = " | ".join(x["titulo"] for x in s)
        self.assertIn("vermelho", titulos)
        self.assertIn("Reduzir Lazer", titulos)
        self.assertIn("Lazer subiu 100%", titulos)
        self.assertIn("Assinaturas somam", titulos)


class TestAPI(unittest.TestCase):
    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.client = create_app(self.db).test_client()

    def tearDown(self):
        os.remove(self.db)

    def test_fluxo_completo(self):
        c = self.client
        self.assertEqual(c.post("/api/v1/receitas-fixas", json={"descricao": "Salário", "valor": 5000}).status_code, 201)
        cats = {x["nome"]: x["id"] for x in c.get("/api/v1/categorias").get_json()}
        c.post("/api/v1/despesas-fixas", json={"descricao": "Aluguel", "valor": 1500, "categoria_id": cats["Moradia"]})
        c.post("/api/v1/lancamentos", json={"data": "2026-11-05", "descricao": "Cinema", "valor": 500,
                                            "tipo": "despesa", "categoria_id": cats["Lazer"]})
        c.post("/api/v1/lancamentos", json={"data": "2026-10-05", "descricao": "Outro mês", "valor": 999,
                                            "tipo": "despesa"})

        r = c.get("/api/v1/resumo?mes=2026-11").get_json()
        self.assertEqual(r["renda"], 5000)
        self.assertEqual(r["gastos"], 2000)
        self.assertEqual(r["saldo"], 3000)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(len(r["historico"]), 6)
        self.assertEqual(r["por_categoria"][0]["nome"], "Moradia")

        c.post("/api/v1/objetivos", json={"nome": "Viagem", "valor_alvo": 9000})
        p = c.get("/api/v1/objetivos/plano?mes=2026-11").get_json()
        self.assertEqual(p["meses_total"], 3)
        self.assertEqual(p["conclusao_total"], "2027-02")

        self.assertEqual(c.get("/api/v1/sugestoes?mes=2026-11").status_code, 200)

    def test_validacao(self):
        r = self.client.post("/api/v1/receitas-fixas", json={"descricao": "", "valor": 10})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/v1/lancamentos", json={"data": "2026-11-01", "descricao": "x", "valor": -5, "tipo": "despesa"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.get("/api/v1/resumo?mes=2026-13").status_code, 400)
        self.assertEqual(self.client.delete("/api/v1/objetivos/999").status_code, 404)

    def test_atualizar_e_excluir(self):
        o = self.client.post("/api/v1/objetivos", json={"nome": "Carro", "valor_alvo": 40000}).get_json()
        u = self.client.put(f"/api/v1/objetivos/{o['id']}", json={"valor_guardado": 1000}).get_json()
        self.assertEqual(u["valor_guardado"], 1000)
        self.assertEqual(self.client.delete(f"/api/v1/objetivos/{o['id']}").status_code, 204)

    def test_parcelamento(self):
        c = self.client
        c.post("/api/v1/receitas-fixas", json={"descricao": "Salário", "valor": 3000})
        # 12 mil em 10x a partir de nov/2026 -> R$ 1.200 por mês até ago/2027
        r = c.post("/api/v1/parcelamentos", json={"descricao": "Notebook", "valor_total": 12000,
                                                  "num_parcelas": 10, "primeira_parcela": "2026-11"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["valor_parcela"], 1200)

        pid = r.get_json()["id"]
        p = c.get("/api/v1/parcelamentos?mes=2027-01").get_json()[0]
        self.assertEqual((p["status"], p["parcela_atual"]), ("ativo", 3))
        self.assertEqual(p["valor_restante"], 12000)  # nada marcado como pago ainda

        # marca as 3 primeiras como pagas
        pags = [{"numero": k, "data_pagamento": f"2026-{10 + k}-05" if k < 3 else "2027-01-05"} for k in (1, 2, 3)]
        self.assertEqual(c.put(f"/api/v1/parcelamentos/{pid}/pagamentos", json={"pagamentos": pags}).status_code, 200)
        p = c.get("/api/v1/parcelamentos?mes=2027-01").get_json()[0]
        self.assertEqual((p["parcelas_pagas"], p["proxima_parcela"]), (3, 4))
        self.assertEqual(p["valor_restante"], 8400)
        self.assertEqual(p["ultimo_pagamento"], "2027-01-05")
        lista = c.get(f"/api/v1/parcelamentos/{pid}/pagamentos").get_json()
        self.assertEqual(len(lista), 10)
        self.assertTrue(lista[2]["pago"])
        self.assertFalse(lista[3]["pago"])
        bad = c.put(f"/api/v1/parcelamentos/{pid}/pagamentos", json={"pagamentos": [{"numero": 11, "data_pagamento": "2027-01-01"}]})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(p["ultima_parcela"], "2027-08")
        self.assertEqual(c.get("/api/v1/parcelamentos?mes=2026-10").get_json()[0]["status"], "futuro")
        self.assertEqual(c.get("/api/v1/parcelamentos?mes=2027-09").get_json()[0]["status"], "quitado")

        self.assertEqual(c.get("/api/v1/resumo?mes=2026-11").get_json()["saldo"], 1800)
        self.assertEqual(c.get("/api/v1/resumo?mes=2027-09").get_json()["saldo"], 3000)

        proj = c.get("/api/v1/projecao?mes=2027-07&meses=3").get_json()
        self.assertEqual([m["parcelas"] for m in proj], [1200, 1200, 0])

        # parcela com juros informada pelo usuário
        r = c.post("/api/v1/parcelamentos", json={"descricao": "Empréstimo", "tipo": "divida", "valor_total": 5000,
                                                  "num_parcelas": 12, "valor_parcela": 500, "primeira_parcela": "2026-11"})
        j = c.get("/api/v1/parcelamentos?mes=2026-11").get_json()
        self.assertEqual([x["juros"] for x in j if x["descricao"] == "Empréstimo"], [1000])
        self.assertEqual(c.get("/api/v1/resumo?mes=2026-11").get_json()["saldo"], 1300)  # 3000-1200-500
        self.assertEqual(c.get("/api/v1/sugestoes?mes=2026-11").status_code, 200)

        bad = c.post("/api/v1/parcelamentos", json={"descricao": "X", "valor_total": 100, "num_parcelas": 0,
                                                    "primeira_parcela": "2026-11"})
        self.assertEqual(bad.status_code, 400)

    def test_renda_dividida_e_fluxo_diario(self):
        c = self.client
        # Salário de 3000: 1200 de adiantamento no dia 20 e 1800 no dia 5
        r = c.post("/api/v1/receitas-fixas", json={"descricao": "Salário", "valor": 3000, "dia_recebimento": 5,
                                                   "valor_2": 1200, "dia_recebimento_2": 20})
        self.assertEqual(r.status_code, 201)
        c.post("/api/v1/despesas-fixas", json={"descricao": "Aluguel", "valor": 1500, "dia_vencimento": 1})
        c.post("/api/v1/parcelamentos", json={"descricao": "Cartão", "valor_total": 400, "num_parcelas": 1,
                                              "primeira_parcela": "2026-11", "dia_vencimento": 10})
        c.post("/api/v1/despesas-fixas", json={"descricao": "Sem data", "valor": 100})

        f = c.get("/api/v1/fluxo?mes=2026-11").get_json()
        self.assertEqual([(e["dia"], e["valor"]) for e in f["eventos"]],
                         [(1, -1500), (5, 1800), (10, -400), (20, 1200)])
        self.assertEqual(f["menor_saldo"], -1500)
        # -1500 (dia 1) +1800 (dia 5) = 300; -400 (dia 10) = -100 até o adiantamento do dia 20
        self.assertEqual(f["periodos_negativos"], [{"de": 1, "ate": 4}, {"de": 10, "ate": 19}])
        self.assertEqual(f["saldo_dias_definidos"], 1100)
        self.assertEqual(f["saldo_final"], 1000)
        self.assertEqual(f["dias"][29]["saldo"], 1100)  # dia 30

        # o 2º pagamento precisa de dia e ser menor que o total
        self.assertEqual(c.post("/api/v1/receitas-fixas", json={"descricao": "X", "valor": 100, "valor_2": 50}).status_code, 400)
        self.assertEqual(c.post("/api/v1/receitas-fixas", json={"descricao": "X", "valor": 100, "valor_2": 100,
                                                                "dia_recebimento_2": 3}).status_code, 400)
        dicas = " ".join(d["titulo"] for d in c.get("/api/v1/sugestoes?mes=2026-11").get_json())
        self.assertIn("Falta dinheiro do dia 1 ao dia 4", dicas)

    def test_dia_31_em_fevereiro(self):
        from services.parcelas import data_no_mes
        self.assertEqual(data_no_mes("2027-02", 31), "2027-02-28")

    def test_simular_endpoint(self):
        r = self.client.post("/api/v1/simular", json={"metas": [{"nome": "V", "valor": 8000},
                                                               {"nome": "I", "valor": 20000}],
                                                     "prazo_meses": 14})
        self.assertEqual(r.get_json()["mensal_necessario"], 2000)
        self.assertEqual(self.client.post("/api/v1/simular", json={"metas": []}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
