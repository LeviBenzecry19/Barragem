"""Testes de integração: banco de dados, regras de alerta e API HTTP."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from monitor import config
from monitor.banco import Banco
from monitor.servico import ErroValidacao, Monitor
from monitor.servidor import criar_servidor
from simulador import simulador


def pacote(**leituras):
    return {"estacao": "T-01", "leituras": leituras}


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.banco = Banco(":memory:")
        self.monitor = Monitor(self.banco)

    def tearDown(self):
        self.banco.fechar()

    def test_registra_e_avalia(self):
        r = self.monitor.registrar(pacote(nivel_reservatorio=10.0, pressao_poros=15.0))
        self.assertEqual(r["avaliacao"]["nivel"], "Normal")
        self.assertEqual(set(self.banco.ultimas_leituras()), {"nivel_reservatorio", "pressao_poros"})
        self.assertEqual(len(self.banco.historico("pressao_poros")), 1)

    def test_avaliacao_usa_ultima_leitura_de_cada_sensor(self):
        self.monitor.registrar(pacote(pressao_poros=40.0))
        r = self.monitor.registrar(pacote(nivel_reservatorio=10.0))
        self.assertIn("pressao_poros", r["avaliacao"]["variaveis"])
        self.assertEqual(r["avaliacao"]["variaveis"]["pressao_poros"]["nivel"], "Alerta")

    def test_alerta_ao_subir_de_nivel(self):
        self.monitor.registrar(pacote(vazao_infiltracao=20.0))
        r = self.monitor.registrar(pacote(vazao_infiltracao=55.0))
        origens = {a["origem"]: a["nivel"] for a in r["alertas_gerados"]}
        self.assertEqual(origens["vazao_infiltracao"], "Alerta")

    def test_sem_alerta_repetido_enquanto_pendente(self):
        for valor in (20.0, 55.0, 45.0, 55.0, 45.0, 55.0):
            self.monitor.registrar(pacote(vazao_infiltracao=valor))
        da_vazao = [a for a in self.banco.alertas() if a["origem"] == "vazao_infiltracao"]
        self.assertEqual(len(da_vazao), 1)

    def test_novo_alerta_apos_reconhecer(self):
        self.monitor.registrar(pacote(vazao_infiltracao=55.0))
        alerta = [a for a in self.banco.alertas() if a["origem"] == "vazao_infiltracao"][0]
        self.assertTrue(self.banco.reconhecer_alerta(alerta["id"]))
        self.monitor.registrar(pacote(vazao_infiltracao=20.0))
        r = self.monitor.registrar(pacote(vazao_infiltracao=55.0))
        self.assertTrue(any(a["origem"] == "vazao_infiltracao" for a in r["alertas_gerados"]))

    def test_escalada_gera_alerta_mesmo_com_pendente(self):
        self.monitor.registrar(pacote(vazao_infiltracao=40.0))   # Atenção
        r = self.monitor.registrar(pacote(vazao_infiltracao=80.0))  # Crítico
        self.assertIn(("vazao_infiltracao", "Crítico"),
                      [(a["origem"], a["nivel"]) for a in r["alertas_gerados"]])

    def test_validacao(self):
        for invalido in (None, [], {"leituras": {}}, pacote(sensor_x=1), pacote(nivel_reservatorio="10"),
                         pacote(nivel_reservatorio=True), pacote(nivel_reservatorio=float("nan")),
                         {"leituras": {"recalque": 1}, "instante": "ontem"}):
            with self.assertRaises(ErroValidacao, msg=repr(invalido)):
                self.monitor.registrar(invalido)

    def test_instante_convertido_para_utc(self):
        r = self.monitor.registrar({"instante": "2026-01-01T09:00:00-03:00", "leituras": {"recalque": 5}})
        self.assertEqual(r["instante"], "2026-01-01T12:00:00Z")


class TestCenariosSimulados(unittest.TestCase):
    """Detecção de alterações simuladas (indicador de avaliação do projeto)."""

    def rodar(self, cenario, passos=150):
        import random
        banco = Banco(":memory:")
        monitor = Monitor(banco)
        rng, acum = random.Random(1), {}
        niveis = []
        for i in range(passos):
            p = i / (passos - 1)
            leit = simulador.gerar_leitura(cenario, p, (i * 24 / passos) % 24, rng, acum)
            niveis.append(monitor.registrar({"leituras": leit})["avaliacao"]["nivel"])
        banco.fechar()
        return niveis

    def pior(self, niveis):
        return max(niveis, key=config.NIVEIS.index)

    def test_normal_permanece_normal(self):
        self.assertEqual(self.pior(self.rodar("normal")), "Normal")

    def test_cheia_atinge_alerta(self):
        self.assertEqual(self.pior(self.rodar("cheia")), "Alerta")

    def test_infiltracao_atinge_critico(self):
        niveis = self.rodar("infiltracao")
        self.assertEqual(niveis[0], "Normal")
        self.assertEqual(niveis[-1], "Crítico")

    def test_sismo_gera_alerta(self):
        self.assertIn(self.pior(self.rodar("sismo")), ("Alerta", "Crítico"))


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banco = Banco(":memory:")
        cls.servidor = criar_servidor(cls.banco, "127.0.0.1", 0, chave_api="segredo")
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.banco.fechar()

    def req(self, caminho, corpo=None, chave="segredo"):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        r = urllib.request.Request(self.base + caminho, data=dados, method="POST" if dados else "GET")
        r.add_header("Content-Type", "application/json")
        if chave:
            r.add_header("X-Chave-API", chave)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_fluxo_completo(self):
        status, r = self.req("/api/leituras", pacote(pressao_poros=50.0, nivel_reservatorio=11.0))
        self.assertEqual(status, 201)
        self.assertEqual(r["avaliacao"]["nivel"], "Crítico")

        status, estado = self.req("/api/estado")
        self.assertEqual(status, 200)
        self.assertEqual(estado["avaliacao"]["nivel"], "Crítico")
        self.assertEqual(len(estado["sensores"]), len(config.VARIAVEIS))

        _, hist = self.req("/api/historico?variavel=pressao_poros&horas=1")
        self.assertEqual(hist["pontos"][-1]["valor"], 50.0)

        _, alertas = self.req("/api/alertas")
        self.assertTrue(alertas["alertas"])
        alerta_id = alertas["alertas"][0]["id"]
        status, _ = self.req(f"/api/alertas/{alerta_id}/reconhecer", {})
        self.assertEqual(status, 200)

    def test_chave_api_obrigatoria(self):
        status, _ = self.req("/api/leituras", pacote(recalque=1.0), chave="errada")
        self.assertEqual(status, 401)

    def test_erros(self):
        self.assertEqual(self.req("/api/leituras", pacote(xyz=1))[0], 400)
        self.assertEqual(self.req("/api/historico?variavel=xyz")[0], 400)
        self.assertEqual(self.req("/api/nao-existe")[0], 404)
        self.assertEqual(self.req("/static/../servidor.py")[0], 404)

    def test_dashboard(self):
        with urllib.request.urlopen(self.base + "/") as resp:
            self.assertIn(b"Monitoramento", resp.read())


if __name__ == "__main__":
    unittest.main()
