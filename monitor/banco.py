"""Camada de banco de dados (SQLite). Modelo descrito em docs/05-banco-de-dados.md."""

import json
import sqlite3
import threading

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sensores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    variavel    TEXT NOT NULL UNIQUE,
    nome        TEXT NOT NULL,
    unidade     TEXT NOT NULL,
    equipamento TEXT NOT NULL,
    base        REAL NOT NULL,
    atencao     REAL NOT NULL,
    alerta      REAL NOT NULL,
    critico     REAL NOT NULL,
    peso        REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS leituras (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id INTEGER NOT NULL REFERENCES sensores(id),
    estacao   TEXT NOT NULL,
    instante  TEXT NOT NULL,          -- ISO 8601, UTC
    valor     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_leituras_sensor_instante ON leituras(sensor_id, instante);

CREATE TABLE IF NOT EXISTS avaliacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instante        TEXT NOT NULL,
    indice          REAL NOT NULL,
    fator_seguranca REAL,
    nivel           TEXT NOT NULL,
    detalhes        TEXT NOT NULL     -- JSON com o resultado completo de analise.avaliar
);
CREATE INDEX IF NOT EXISTS ix_avaliacoes_instante ON avaliacoes(instante);

CREATE TABLE IF NOT EXISTS alertas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    instante     TEXT NOT NULL,
    origem       TEXT NOT NULL,       -- chave da variável ou 'global'
    nivel        TEXT NOT NULL,
    nivel_anterior TEXT NOT NULL,
    valor        REAL,
    mensagem     TEXT NOT NULL,
    reconhecido  INTEGER NOT NULL DEFAULT 0
);
"""


class Banco:
    def __init__(self, caminho="barragem.db"):
        self.caminho = caminho
        self._con = sqlite3.connect(caminho, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._trava = threading.Lock()
        with self._trava:
            self._con.executescript(ESQUEMA)
            self._sincronizar_sensores()

    def _sincronizar_sensores(self):
        for v in config.VARIAVEIS.values():
            self._con.execute(
                """INSERT INTO sensores (variavel, nome, unidade, equipamento, base, atencao, alerta, critico, peso)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(variavel) DO UPDATE SET
                     nome=excluded.nome, unidade=excluded.unidade, equipamento=excluded.equipamento,
                     base=excluded.base, atencao=excluded.atencao, alerta=excluded.alerta,
                     critico=excluded.critico, peso=excluded.peso""",
                (v.chave, v.nome, v.unidade, v.equipamento, v.base, v.atencao, v.alerta, v.critico, v.peso),
            )
        self._con.commit()

    def fechar(self):
        self._con.close()

    # -- escrita ----------------------------------------------------------

    def inserir_leituras(self, estacao, instante, leituras):
        with self._trava:
            ids = {r["variavel"]: r["id"] for r in self._con.execute("SELECT id, variavel FROM sensores")}
            self._con.executemany(
                "INSERT INTO leituras (sensor_id, estacao, instante, valor) VALUES (?, ?, ?, ?)",
                [(ids[k], estacao, instante, float(v)) for k, v in leituras.items()],
            )
            self._con.commit()

    def inserir_avaliacao(self, instante, resultado):
        with self._trava:
            self._con.execute(
                "INSERT INTO avaliacoes (instante, indice, fator_seguranca, nivel, detalhes) VALUES (?, ?, ?, ?, ?)",
                (instante, resultado["indice"], resultado["fator_seguranca"], resultado["nivel"],
                 json.dumps(resultado, ensure_ascii=False)),
            )
            self._con.commit()

    def inserir_alerta(self, instante, origem, nivel, nivel_anterior, valor, mensagem):
        with self._trava:
            cur = self._con.execute(
                """INSERT INTO alertas (instante, origem, nivel, nivel_anterior, valor, mensagem)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (instante, origem, nivel, nivel_anterior, valor, mensagem),
            )
            self._con.commit()
            return cur.lastrowid

    def reconhecer_alerta(self, alerta_id):
        with self._trava:
            cur = self._con.execute("UPDATE alertas SET reconhecido = 1 WHERE id = ?", (alerta_id,))
            self._con.commit()
            return cur.rowcount > 0

    # -- leitura ----------------------------------------------------------

    def _consultar(self, sql, params=()):
        with self._trava:
            return [dict(r) for r in self._con.execute(sql, params)]

    def sensores(self):
        return self._consultar("SELECT * FROM sensores ORDER BY id")

    def ultimas_leituras(self):
        """Última leitura de cada variável: {chave: {valor, instante, estacao}}."""
        linhas = self._consultar(
            """SELECT s.variavel, l.valor, l.instante, l.estacao
               FROM leituras l JOIN sensores s ON s.id = l.sensor_id
               WHERE l.id IN (SELECT MAX(id) FROM leituras GROUP BY sensor_id)"""
        )
        return {r["variavel"]: {k: r[k] for k in ("valor", "instante", "estacao")} for r in linhas}

    def historico(self, variavel, desde=None, limite=2000):
        sql = """SELECT l.instante, l.valor FROM leituras l JOIN sensores s ON s.id = l.sensor_id
                 WHERE s.variavel = ?"""
        params = [variavel]
        if desde:
            sql += " AND l.instante >= ?"
            params.append(desde)
        sql += " ORDER BY l.instante DESC, l.id DESC LIMIT ?"
        params.append(limite)
        return list(reversed(self._consultar(sql, params)))

    def historico_indice(self, desde=None, limite=2000):
        sql = "SELECT instante, indice, fator_seguranca, nivel FROM avaliacoes"
        params = []
        if desde:
            sql += " WHERE instante >= ?"
            params.append(desde)
        sql += " ORDER BY instante DESC, id DESC LIMIT ?"
        params.append(limite)
        return list(reversed(self._consultar(sql, params)))

    def ultima_avaliacao(self):
        linhas = self._consultar("SELECT detalhes, instante FROM avaliacoes ORDER BY id DESC LIMIT 1")
        if not linhas:
            return None
        resultado = json.loads(linhas[0]["detalhes"])
        resultado["instante"] = linhas[0]["instante"]
        return resultado

    def niveis_pendentes(self):
        """Nível mais severo entre os alertas não reconhecidos de cada origem."""
        niveis = {}
        for r in self._consultar("SELECT origem, nivel FROM alertas WHERE reconhecido = 0"):
            atual = niveis.get(r["origem"])
            if atual is None or config.NIVEIS.index(r["nivel"]) > config.NIVEIS.index(atual):
                niveis[r["origem"]] = r["nivel"]
        return niveis

    def alertas(self, apenas_pendentes=False, limite=100):
        sql = "SELECT * FROM alertas"
        if apenas_pendentes:
            sql += " WHERE reconhecido = 0"
        sql += " ORDER BY id DESC LIMIT ?"
        return self._consultar(sql, (limite,))
