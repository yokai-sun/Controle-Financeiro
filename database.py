"""Conexão com o SQLite e criação das tabelas."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "FINANCAS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "financas.db")
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT NOT NULL DEFAULT '#64748b',
    essencial INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS receitas_fixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS despesas_fixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL,
    dia_vencimento INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS lancamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS parcelamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'compra' CHECK (tipo IN ('compra', 'divida')),
    valor_total REAL NOT NULL,
    num_parcelas INTEGER NOT NULL,
    valor_parcela REAL NOT NULL,
    primeira_parcela TEXT NOT NULL,  -- AAAA-MM
    categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pagamentos_parcela (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcelamento_id INTEGER NOT NULL REFERENCES parcelamentos(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,           -- nº da parcela (1..n)
    data_pagamento TEXT NOT NULL,      -- AAAA-MM-DD
    UNIQUE (parcelamento_id, numero)
);

CREATE TABLE IF NOT EXISTS objetivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    valor_alvo REAL NOT NULL,
    valor_guardado REAL NOT NULL DEFAULT 0,
    prazo_meses INTEGER,
    prioridade INTEGER NOT NULL DEFAULT 1,
    icone TEXT NOT NULL DEFAULT '🎯'
);

CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""

CATEGORIAS_PADRAO = [
    ("Moradia", "#6366f1", 1),
    ("Alimentação", "#f59e0b", 1),
    ("Transporte", "#0ea5e9", 1),
    ("Saúde", "#10b981", 1),
    ("Educação", "#8b5cf6", 1),
    ("Lazer", "#ec4899", 0),
    ("Assinaturas", "#ef4444", 0),
    ("Compras", "#f97316", 0),
    ("Outros", "#64748b", 0),
]

CONFIG_PADRAO = {"percentual_metas": "100"}

# Colunas adicionadas depois da 1ª versão (bancos existentes recebem via ALTER TABLE)
MIGRACOES = [
    ("receitas_fixas", "dia_recebimento", "INTEGER"),
    ("receitas_fixas", "valor_2", "REAL NOT NULL DEFAULT 0"),  # parte paga no 2º dia (adiantamento)
    ("receitas_fixas", "dia_recebimento_2", "INTEGER"),
    ("parcelamentos", "dia_vencimento", "INTEGER"),
]


def _migrar(conn):
    for tabela, coluna, tipo in MIGRACOES:
        existentes = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        if coluna not in existentes:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


def get_conn(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def conexao(path=None):
    """Abre a conexão, faz commit (ou rollback em erro) e sempre fecha."""
    conn = get_conn(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path=None):
    conn = get_conn(path)
    conn.executescript(SCHEMA)
    _migrar(conn)
    if conn.execute("SELECT COUNT(*) FROM categorias").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO categorias (nome, cor, essencial) VALUES (?, ?, ?)", CATEGORIAS_PADRAO
        )
    for chave, valor in CONFIG_PADRAO.items():
        conn.execute("INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()


def get_config(conn, chave, padrao=None):
    row = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
    return row["valor"] if row else padrao
