import math
import unittest

from monitor import analise, config, tendencias

PESOS = analise.pesos_especificos(config.MACICO["densidade_graos"], config.MACICO["indice_vazios"],
                                  config.MACICO["umidade"])


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
        args = (PESOS["natural"], g["profundidade_ruptura"], g["inclinacao_talude_graus"],
                g["coesao_efetiva"], g["angulo_atrito_graus"])
        fs = [analise.fator_seguranca_talude_infinito(u, *args) for u in (0, 15, 30, 45)]
        self.assertEqual(fs, sorted(fs, reverse=True))

    def test_limites_pressao_coerentes_com_faixas_fs(self):
        # Os limites do piezômetro coincidem com as faixas do FS mínimo da varredura.
        var = config.VARIAVEIS["pressao_poros"]
        fs = lambda u: analise.avaliar({"pressao_poros": u})["fator_seguranca"]  # noqa: E731
        self.assertEqual(analise.classificar_fs(fs(var.base)), "Normal")
        self.assertEqual(analise.classificar_fs(fs(var.atencao)), "Atenção")
        self.assertEqual(analise.classificar_fs(fs(var.alerta)), "Alerta")
        self.assertEqual(analise.classificar_fs(fs(var.critico)), "Crítico")

    def test_pesos_especificos(self):
        # Gs = 2,70, e = 0,60, w = 15%: γd ≈ 16,55, γnat ≈ 19,04, γsat ≈ 20,23 kN/m³
        self.assertAlmostEqual(PESOS["seco"], 16.554, places=2)
        self.assertAlmostEqual(PESOS["natural"], 19.04, places=2)
        self.assertAlmostEqual(PESOS["saturado"], 20.233, places=2)

    def test_fs_geral_igual_ao_original_sem_sismo(self):
        original = analise.fator_seguranca_talude_infinito(20, 19, 5, 21.8, 15, 32)
        geral = analise.fs_talude_infinito_geral(19 * 5, 20, 21.8, 15, 32)
        self.assertAlmostEqual(original, geral, places=9)

    def test_varredura_acha_superficie_mais_profunda(self):
        # Com c' > 0 o FS cai com a profundidade: a superfície crítica não é a do piezômetro.
        g = config.GEOTECNIA
        v = analise.varredura_profundidade(15, 5, PESOS["natural"], PESOS["saturado"], 21.8, 15, 32, 8, 0.25)
        self.assertEqual(v["z"], 8)
        fs_5m = analise.fs_talude_infinito_geral(
            analise.tensao_vertical(5, v["zw"], PESOS["natural"], PESOS["saturado"]), 15,
            g["inclinacao_talude_graus"], g["coesao_efetiva"], g["angulo_atrito_graus"])
        self.assertLess(v["fs"], fs_5m)

    def test_sismo_e_rebaixamento_reduzem_fs(self):
        args = (PESOS["natural"], PESOS["saturado"], 21.8, 15, 32, 8, 0.25)
        estatico = analise.varredura_profundidade(15, 5, *args)["fs"]
        self.assertLess(analise.varredura_profundidade(15, 5, *args, kh=0.1)["fs"], estatico)
        # Montante: saturado e sem empuxo do reservatório vs. o mesmo talude seco.
        rebaixado = analise.fs_rebaixamento_rapido(PESOS["saturado"], 18.4, 15, 32, 8, 0.25)["fs"]
        seco = analise.fs_talude_infinito_geral(PESOS["saturado"] * 8, 0, 18.4, 15, 32)
        self.assertLess(rebaixado, seco)

    def test_gradiente_critico(self):
        self.assertAlmostEqual(analise.gradiente_critico(PESOS["saturado"]), 1.0625, places=3)
        self.assertAlmostEqual(analise.gradiente_hidraulico(6, 0, 20), 0.3)

    def test_onda_e_sobrelevacao(self):
        self.assertEqual(analise.altura_onda(0, 1.5), 0)
        # 100 km/h, pista de 10 km, profundidade 10 m
        self.assertAlmostEqual(analise.altura_onda(100, 10), 1.419, places=2)
        self.assertAlmostEqual(analise.sobrelevacao_vento(100, 10, 10), 0.161, places=3)
        self.assertAlmostEqual(analise.borda_livre_efetiva(15, 200, 12, 0.5, 0.1), 2.2)

    def test_balanco_hidrico_converge_para_equilibrio(self):
        # Afluência constante: o nível tende ao ponto em que o vertedouro devolve a vazão.
        res = config.RESERVATORIO
        q = 40.0
        esperado = res["cota_soleira_vertedouro_m"] + (
            (q - res["vazao_tomada_m3s"]) / (res["coef_descarga_vertedouro"] * res["largura_vertedouro_m"])) ** (2 / 3)
        prev = analise.prever_nivel(12.0, q, 240, 99)
        self.assertAlmostEqual(prev["nivel_final"], esperado, delta=0.05)
        self.assertIsNone(prev["horas_ate_galgamento"])
        self.assertIsNotNone(analise.prever_nivel(13.0, 100.0, 24, 15.0)["horas_ate_galgamento"])

    def test_confiabilidade_reprodutivel_e_coerente(self):
        fs_de = lambda u: (lambda c, phi: analise.fs_talude_infinito_geral(150, u, 21.8, c, phi))  # noqa: E731
        a = analise.confiabilidade(fs_de(20), 15, 32, 0.2, 0.1, 500)
        self.assertEqual(a, analise.confiabilidade(fs_de(20), 15, 32, 0.2, 0.1, 500))
        b = analise.confiabilidade(fs_de(60), 15, 32, 0.2, 0.1, 500)
        self.assertGreater(b["prob_ruptura"], a["prob_ruptura"])
        self.assertLess(b["beta"], a["beta"])

    def test_classificar_abaixo_e_acima(self):
        self.assertEqual(analise.classificar_abaixo(0.4, config.FAIXAS_BORDA_LIVRE), "Crítico")
        self.assertEqual(analise.classificar_abaixo(2.0, config.FAIXAS_BORDA_LIVRE), "Normal")
        self.assertEqual(analise.classificar_acima(3.0, (2, 3, 4)), "Alerta")
        self.assertEqual(analise.classificar_acima(-9, (2, 3, 4)), "Normal")


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
        leit["temperatura"] = 70
        r = analise.avaliar(leit)
        self.assertEqual(r["indice"], 0.0)
        self.assertEqual(r["variaveis"]["temperatura"]["nivel"], "Crítico")
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


def modo(resultado, chave):
    return next(m for m in resultado["modos"] if m["chave"] == chave)


class TestModosDeRuptura(unittest.TestCase):
    def test_tudo_normal_em_todos_os_modos(self):
        r = analise.avaliar(leituras_normais())
        for m in r["modos"]:
            self.assertIn(m["nivel"], (None, "Normal"), m["chave"])
        # Sem histórico, os modos que só dependem dele ficam sem dados.
        self.assertIsNone(modo(r, "talude_montante")["nivel"])
        self.assertIsNone(modo(r, "deformacoes")["nivel"])

    def test_sismo_forte_reduz_fs_pseudoestatico(self):
        # A vibração não tem peso no índice, mas entra no FS: não é "diluída".
        leit = leituras_normais()
        leit["vibracao"] = 0.5
        r = analise.avaliar(leit)
        self.assertEqual(r["indice"], 0.0)
        self.assertEqual(modo(r, "sismico")["nivel"], "Crítico")
        self.assertEqual(r["nivel"], "Crítico")

    def test_vibracao_pequena_nao_verifica_sismo(self):
        leit = leituras_normais()
        leit["vibracao"] = 0.02
        sismo = modo(analise.avaliar(leit), "sismico")
        self.assertEqual(sismo["nivel"], "Normal")
        self.assertEqual([i["nome"] for i in sismo["indicadores"]], ["Aceleração de pico"])

    def test_vento_e_recalque_reduzem_borda_livre(self):
        leit = leituras_normais()
        leit["nivel_reservatorio"] = 13.0
        calmo = modo(analise.avaliar({**leit, "vento": 0, "recalque": 0}), "galgamento")["indicadores"][0]["valor"]
        ruim = modo(analise.avaliar({**leit, "vento": 80, "recalque": 50}), "galgamento")["indicadores"][0]["valor"]
        self.assertAlmostEqual(calmo, 2.0, places=3)
        self.assertLess(ruim, calmo - 0.3)

    def test_previsao_de_galgamento_pela_afluencia(self):
        leit = leituras_normais()
        leit.update(nivel_reservatorio=13.0, vazao_afluente=100.0)
        r = analise.avaliar(leit)
        self.assertEqual(modo(r, "galgamento")["nivel"], "Crítico")
        self.assertEqual(r["nivel"], "Crítico")
        self.assertTrue(any("galgamento em" in i["detalhe"] for i in modo(r, "galgamento")["indicadores"]))

    def test_turbidez_com_vazao_alta_indica_piping(self):
        leit = leituras_normais()
        leit.update(turbidez=60, vazao_infiltracao=55)
        self.assertEqual(modo(analise.avaliar(leit), "erosao_interna")["nivel"], "Crítico")
        leit["vazao_infiltracao"] = config.VARIAVEIS["vazao_infiltracao"].base
        self.assertEqual(modo(analise.avaliar(leit), "erosao_interna")["nivel"], "Normal")

    def test_rebaixamento_rapido_avalia_montante(self):
        leit = leituras_normais()
        lento = analise.avaliar(leit, contexto={"taxas": {"nivel_reservatorio": -0.1}})
        self.assertEqual(modo(lento, "talude_montante")["nivel"], "Normal")
        self.assertEqual(len(modo(lento, "talude_montante")["indicadores"]), 1)
        rapido = analise.avaliar(leit, contexto={"taxas": {"nivel_reservatorio": -2.0}})
        self.assertEqual(modo(rapido, "talude_montante")["nivel"], "Atenção")

    def test_taxas_residuos_e_fukuzono_entram_nos_modos(self):
        ctx = {
            "taxas": {"deslocamento_horizontal": 12.0},
            "residuos": {"vazao_infiltracao": {"medido": 40, "previsto": 20, "desvio": 4, "z": 5.0, "pontos": 100}},
            "fukuzono": {"horas": 30.0, "velocidade": 12.0},
        }
        r = analise.avaliar(leituras_normais(), contexto=ctx)
        # Deformações: taxa crítica confirmada pelo Fukuzono (Alerta) → Crítico.
        self.assertEqual(modo(r, "deformacoes")["nivel"], "Crítico")
        # Erosão interna: resíduo crítico, mas FS de piping normal → fica em Alerta.
        self.assertEqual(modo(r, "erosao_interna")["nivel"], "Alerta")
        self.assertTrue(modo(r, "erosao_interna")["limitado"])
        self.assertTrue(any("Fukuzono" in m for m in r["motivos"]))
        self.assertTrue(any("sem confirmação" in m for m in r["motivos"]))

    def test_chuva_antecedente_umedece_o_macico(self):
        seco = analise.avaliar(leituras_normais(), contexto={"api_mm": 0})
        umido = analise.avaliar(leituras_normais(), contexto={"api_mm": 300})
        self.assertGreater(umido["derivados"]["tensao_total_kpa"], seco["derivados"]["tensao_total_kpa"])
        self.assertEqual(umido["derivados"]["chuva_antecedente_mm"], 300)


class TestTendencias(unittest.TestCase):
    H = 3600.0

    def test_taxa_diaria(self):
        serie = [(i * self.H, 10 + 0.5 * i) for i in range(25)]   # +0,5 por hora
        self.assertAlmostEqual(tendencias.taxa_diaria(serie, 24 * self.H, 24, 6), 12.0)
        self.assertIsNone(tendencias.taxa_diaria(serie[:3], 2 * self.H, 24, 6))   # pouco tempo

    def test_chuva_antecedente(self):
        dia = tendencias.DIA
        serie = [(0.0, 10.0), (dia, 0.0), (2 * dia, 20.0)]
        # API = 20 + 0,9·0 + 0,81·10
        self.assertAlmostEqual(tendencias.chuva_antecedente(serie, 2 * dia, 0.9, 30), 28.1)
        self.assertIsNone(tendencias.chuva_antecedente([], 0, 0.9, 30))

    def test_fukuzono_preve_ruptura_quando_acelera(self):
        # Deslocamento x = −k·ln(1 − t/tf): 1/v cai linearmente até zero em tf.
        tf = 100 * self.H
        serie = [(t, -20 * math.log(1 - t / tf)) for t in [i * self.H for i in range(73)]]
        r = tendencias.velocidade_inversa(serie, 72 * self.H, 72, 6, 0.5)
        self.assertAlmostEqual(r["horas"], 28, delta=4)
        constante = [(i * self.H, 5 + 0.1 * i) for i in range(73)]
        self.assertIsNone(tendencias.velocidade_inversa(constante, 72 * self.H, 72, 6, 0.5))

    def test_modelo_esperado_detecta_desvio(self):
        cfg = config.TENDENCIAS
        nivel = [(i * self.H, 10 + 2 * math.sin(i / 10)) for i in range(200)]
        vazao = [(t, 2 * h + 0.3 * math.sin(t)) for t, h in nivel]   # Q ≈ 2·nível
        series = {"nivel_reservatorio": nivel, "vazao_infiltracao": vazao}
        agora = 200 * self.H
        normal = tendencias.modelo_esperado(series, "vazao_infiltracao", ["nivel_reservatorio"], agora,
                                            {"nivel_reservatorio": 11, "vazao_infiltracao": 22}, cfg, 0.5)
        self.assertAlmostEqual(normal["previsto"], 22, delta=0.3)
        self.assertLess(abs(normal["z"]), 1)
        # Mesma vazão com o reservatório mais baixo: muito acima do esperado.
        anomalo = tendencias.modelo_esperado(series, "vazao_infiltracao", ["nivel_reservatorio"], agora,
                                             {"nivel_reservatorio": 9, "vazao_infiltracao": 22}, cfg, 0.5)
        self.assertGreater(anomalo["z"], 4)

    def test_minimos_quadrados(self):
        linhas = [[1, x] for x in range(10)]
        beta = tendencias.minimos_quadrados(linhas, [3 + 2 * x for x in range(10)], ridge=0)
        self.assertAlmostEqual(beta[0], 3)
        self.assertAlmostEqual(beta[1], 2)


if __name__ == "__main__":
    unittest.main()
