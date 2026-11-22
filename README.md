# 💰 Minhas Finanças

**Aplicativo de controle financeiro pessoal** para entender para onde vai o seu dinheiro, saber se o que você
ganha cobre o que você gasta e planejar objetivos como uma viagem, um intercâmbio, um carro ou uma casa.

Ele roda no seu computador e abre no navegador. **Seus dados ficam só na sua máquina.**

---

## Para que serve?

O app responde, de forma visual, a perguntas do dia a dia:

- **"Estou gastando mais do que ganho?"** Mostra renda, gastos e sobra do mês, com um aviso verde, amarelo
  ou vermelho.
- **"Com o que estou gastando?"** Gráfico por categoria (moradia, alimentação, lazer…) e o histórico dos
  últimos 6 meses.
- **"Em quais dias do mês vai faltar dinheiro?"** Fluxo dia a dia: quando o salário entra e quando cada conta
  vence. Ele avisa, por exemplo, que *"do dia 1 ao 4 o saldo fica negativo"*, mesmo que o mês feche positivo.
- **"Quanto falta das minhas parcelas e dívidas?"** Compras parceladas e empréstimos com parcela atual,
  parcelas pagas (com data), atrasos, juros e mês de término.
- **"Quanto preciso guardar por mês para viajar? Em quantos meses consigo?"** Objetivos com progresso e
  previsão, além de um simulador: *Viagem R$ 8.000 + Intercâmbio R$ 20.000 guardando R$ 1.500/mês = 1 ano e 7
  meses*.
- **"Onde posso economizar?"** Dicas automáticas: regra 50/30/20, maiores gastos não essenciais (e quantos
  meses você antecipa suas metas cortando 20%), categorias que cresceram, assinaturas e parcelas atrasadas.

## Funcionalidades

| Aba | O que tem |
|---|---|
| **Painel** | Renda, gastos, sobra e % da renda comprometida · gráfico por categoria · renda × gastos (6 meses) · **fluxo do mês dia a dia** · resumo dos objetivos |
| **Fixos** | Renda fixa com **dia de recebimento** (inteira ou dividida em duas datas, ex.: adiantamento dia 20 + restante dia 5) · contas fixas com vencimento · **parcelamentos e dívidas** (dia de cobrança, parcelas pagas e quando, atrasos, juros) · projeção de sobra/falta dos próximos 6 meses · categorias |
| **Lançamentos** | Gastos e receitas avulsos do dia a dia, por mês, com filtro por categoria |
| **Objetivos** | Metas com barra de progresso, valor mensal necessário para o prazo e previsão de conclusão pela ordem de prioridade |
| **Simulador** | Junte várias metas e veja quanto guardar por mês **ou** em quantos meses consegue, com linha do tempo |
| **Dicas** | Sugestões de economia calculadas a partir dos seus gastos |

Também tem tema claro e escuro, layout para celular e desktop e campos de dinheiro formatados em R$ enquanto
você digita.

---

## Instalação (Windows)

1. Baixe o projeto: **Code → Download ZIP** no GitHub (e extraia) ou `git clone`.
2. Dê **dois cliques em `install.bat`**. Ele vai:
   - verificar se o **Python 3.10+** está instalado e, se não estiver, oferecer instalar pelo `winget`
     (gerenciador oficial do Windows);
   - instalar as dependências (`Flask`);
   - criar o atalho **"Minhas Finanças"** na Área de Trabalho.
3. Pronto! Para usar, dê dois cliques no atalho. O navegador abre em **http://localhost:5050**.

> A janela do servidor fica **minimizada** na barra de tarefas. O app funciona enquanto ela estiver aberta;
> feche-a para desligar. Clicar no atalho com o app já aberto só abre o navegador.

### Instalação manual (qualquer sistema)

```bash
pip install -r requirements.txt
python app.py
```

Depois abra http://localhost:5050. Para usar outra porta, defina a variável de ambiente `PORT`.

## Seus dados e privacidade

- Tudo fica no arquivo **`financas.db`** (SQLite), criado na pasta do projeto no primeiro uso.
- Esse arquivo **não vai para o GitHub**: está no `.gitignore`.
- **Backup:** basta copiar o `financas.db` para outro lugar (pendrive, nuvem). Para restaurar, coloque-o de
  volta na pasta.

## Usar no celular

No celular, conectado à **mesma rede Wi-Fi** do computador, acesse `http://IP-DO-COMPUTADOR:5050` e use
**"Adicionar à tela inicial"**. O app pode ser instalado como PWA.

---

## Tecnologias

- **Front-end:** HTML, CSS e JavaScript puro · gráficos com [Chart.js](https://www.chartjs.org/) · fonte
  IBM Plex Sans · ícones SVG no estilo Lucide
- **Back-end:** Python + [Flask](https://flask.palletsprojects.com/) · banco SQLite
- **Design:** modo escuro grafite com acento azul. As cores dos gráficos usam uma paleta validada para
  daltonismo e contraste.

## Estrutura

```
app.py              servidor Flask (porta 5050)
database.py         SQLite: tabelas, categorias padrão e migrações automáticas
routes/api.py       API REST (/api/v1)
services/           regras de negócio
  resumo.py         renda, gastos e sobra do mês
  parcelas.py       parcelas, pagamentos, vencimentos e atrasos
  fluxo.py          fluxo de caixa dia a dia
  objetivos.py      metas: quanto guardar e em quantos meses
  sugestoes.py      dicas de economia
templates/          página principal (HTML)
static/             CSS, JavaScript, ícones, manifest e service worker (PWA)
tests/              testes automatizados
install.bat         instalador (Windows)
iniciar.bat         inicia o app (usado pelo atalho)
scripts/            script do instalador
```

## API

Toda a lógica fica em uma API REST JSON. Um futuro app mobile pode usar os mesmos endpoints.

| Método | Rota | Descrição |
|---|---|---|
| GET / POST | `/api/v1/receitas-fixas` · `/despesas-fixas` · `/categorias` · `/objetivos` | Listar / criar |
| GET / POST | `/api/v1/lancamentos?mes=AAAA-MM` | Lançamentos avulsos do mês |
| GET / POST | `/api/v1/parcelamentos?mes=AAAA-MM` | Parcelamentos e dívidas, com a situação no mês |
| GET / PUT | `/api/v1/parcelamentos/<id>/pagamentos` | Parcelas pagas e datas de pagamento |
| GET / PUT / DELETE | `/api/v1/<recurso>/<id>` | Obter / editar / excluir |
| GET | `/api/v1/resumo?mes=AAAA-MM` | Resumo do mês |
| GET | `/api/v1/fluxo?mes=AAAA-MM` | Fluxo de caixa dia a dia |
| GET | `/api/v1/projecao?mes=AAAA-MM&meses=6` | Sobra/falta dos próximos meses |
| GET | `/api/v1/objetivos/plano?mes=AAAA-MM` | Plano das metas |
| POST | `/api/v1/simular` | `{metas:[{nome,valor}], aporte_mensal?, prazo_meses?, ja_guardado?}` |
| GET | `/api/v1/sugestoes?mes=AAAA-MM` | Dicas de economia |
| GET / PUT | `/api/v1/config` | `percentual_metas` (% da sobra destinada às metas) |

## Testes

```bash
python -m unittest discover tests
```
