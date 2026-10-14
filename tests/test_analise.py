import math
import unittest

from monitor import analise, config


class TestFormulas(unittest.TestCase):
    def test_pressao_hidrostatica(self):
        # 10 m de coluna d'água ≈ 98,1 kPa
        self.assertAlmostEqual(analise.pressao_hidrostatica(10), 98.1, places=1)

    def test_carga_piezometrica_inversa(self):
        u = analise.pressao_hidrostatica(7.5)
        self.assertAlmostEqual(analise.carga_piezometrica(u), 7.5, places=6)

    def test_tensao_efetiva(self):
        sigma = analise.tensao_total(19, 5)
        self.assertEqual(sigma, 95)
        self.assertEqual(analise.tensao_efetiva(sigma, 20), 75)

    def test_fs_talude_seco(self):
        # Talude seco e sem coesão: FS = tan φ / tan β
        fs = analise.fator_seguranca_talude_infinito(0, 19, 5, 20, 0, 30)
        self.assertAlmostEqual(fs, math.tan(math.radians(30)) / math.tan(math.radians(20)), places=6)

    def test_fs_diminui_com_poropressao(self):
        g = config.GEOTECNIA
        args = (g["peso_especifico_solo"], g["profundidade_ruptura"], g["inclinacao_talude_graus"],
                g["coesao_efetiva"], g["angulo_atrito_graus"])
        fs = [analise.fator_seguranca_talude_infinito(u, *args) for u in (0, 15, 30, 45)]
        self.assertEqual(fs, sorted(fs, reverse=True))

    def test_limites_pressao_coerentes_com_faixas_fs(self):
        # Os limites do piezômetro foram escolhidos para coincidir com as faixas de FS.
        var = config.VARIAVEIS["pressao_poros"]
        g = config.GEOTECNIA
        fs = lambda u: analise.fator_seguranca_talude_infinito(  # noqa: E731
            u, g["peso_especifico_solo"], g["profundidade_ruptura"], g["inclinacao_talude_graus"],
            g["coesao_efetiva"], g["angulo_atrito_graus"])
        self.assertEqual(analise.classificar_fs(fs(var.base)), "Normal")
        self.assertEqual(analise.classificar_fs(fs(var.alerta)), "Atenção")
        self.assertEqual(analise.classificar_fs(fs(var.critico)), "Alerta")


class TestNormalizacao(unittest.TestCase):
    var = config.Variavel("x", "X", "u", "e", base=10, atencao=20, alerta=30, critico=40, peso=1)

    def test_pontos_de_controle(self):
        self.assertEqual(analise.normalizar(5, self.var), 0.0)
        self.assertEqual(analise.normalizar(10, self.var), 0.0)
        self.assertAlmostEqual(analise.normalizar(20, self.var), 0.25)
        self.assertAlmostEqual(analise.normalizar(25, self.var), 0.375)
        self.assertAlmostEqual(analise.normalizar(30, self.var), 0.50)
        self.assertAlmostEqual(analise.normalizar(40, self.var), 0.75)
        self.assertAlmostEqual(analise.normalizar(45, self.var), 0.875)
        self.assertEqual(analise.normalizar(1000, self.var), 1.0)

    def test_classificacao(self):
        self.assertEqual(analise.classificar_valor(19.9, self.var), "Normal")
        self.assertEqual(analise.classificar_valor(20, self.var), "Atenção")
        self.assertEqual(analise.classificar_valor(30, self.var), "Alerta")
        self.assertEqual(analise.classificar_valor(40, self.var), "Crítico")

    def test_pesos_somam_um(self):
        self.assertAlmostEqual(sum(v.peso for v in config.VARIAVEIS.values()), 1.0)


def leituras_normais():
    return {k: v.base for k, v in config.VARIAVEIS.items()}


class TestAvaliacao(unittest.TestCase):
    def test_tudo_normal(self):
        r = analise.avaliar(leituras_normais())
        self.assertEqual(r["indice"], 0.0)
        self.assertEqual(r["nivel"], "Normal")
        self.assertEqual(r["cobertura"], 1.0)

    def test_uma_variavel_critica_eleva_para_alerta(self):
        # Vazão crítica sozinha dá índice baixo, mas a regra de sobreposição eleva o nível.
        leit = leituras_normais()
        leit["vazao_infiltracao"] = config.VARIAVEIS["vazao_infiltracao"].critico
        r = analise.avaliar(leit)
        self.assertEqual(r["nivel_indice"], "Normal")
        self.assertEqual(r["nivel"], "Alerta")

    def test_duas_variaveis_criticas_eleva_para_critico(self):
        leit = leituras_normais()
        leit["vazao_infiltracao"] = 100
        leit["deslocamento_horizontal"] = 100
        self.assertEqual(analise.avaliar(leit)["nivel"], "Crítico")

    def test_variavel_fora_do_indice_nao_altera_indice(self):
        leit = leituras_normais()
        leit["vibracao"] = 0.5
        r = analise.avaliar(leit)
        self.assertEqual(r["indice"], 0.0)
        self.assertEqual(r["variaveis"]["vibracao"]["nivel"], "Crítico")
        self.assertEqual(r["nivel"], "Alerta")

    def test_indice_todas_em_alerta(self):
        leit = {k: v.alerta for k, v in config.VARIAVEIS.items()}
        r = analise.avaliar(leit)
        self.assertAlmostEqual(r["indice"], 0.5)
        self.assertEqual(r["nivel_indice"], "Alerta")

    def test_fs_baixo_eleva_nivel(self):
        leit = leituras_normais()
        leit["pressao_poros"] = 52  # FS < 1,1
        r = analise.avaliar(leit)
        self.assertLess(r["fator_seguranca"], 1.1)
        self.assertEqual(r["nivel"], "Crítico")

    def test_sensores_faltando_reescalam_pesos(self):
        r = analise.avaliar({"pressao_poros": config.VARIAVEIS["pressao_poros"].alerta})
        self.assertAlmostEqual(r["indice"], 0.5)
        self.assertAlmostEqual(r["cobertura"], 0.25)


if __name__ == "__main__":
    unittest.main()
