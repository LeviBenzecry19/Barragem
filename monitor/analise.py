"""Fórmulas e modelo de classificação/alerta.

Funções puras (sem banco de dados nem rede), para facilitar testes e o
estudo da metodologia. Detalhes em docs/03-metodologia-analise.md.
"""

import math
import random

from . import config
from .config import GAMMA_W, NIVEIS


def br(numero, casas=2):
    """Formata um número com vírgula decimal (padrão brasileiro)."""
    return f"{numero:.{casas}f}".replace(".", ",")


def nivel_max(*niveis):
    """Retorna o nível mais severo entre os informados (None é ignorado)."""
    validos = [n for n in niveis if n]
    return max(validos, key=NIVEIS.index) if validos else None


# ---------------------------------------------------------------------------
# Fórmulas físicas
# ---------------------------------------------------------------------------

def pressao_hidrostatica(h, rho=config.DENSIDADE_AGUA, g=config.GRAVIDADE):
    """P = ρ·g·h, em kPa (h em metros)."""
    return rho * g * h / 1000.0


def carga_piezometrica(u, rho=config.DENSIDADE_AGUA, g=config.GRAVIDADE):
    """Altura de coluna d'água equivalente à pressão de poros: h = u / (ρ·g), em m (u em kPa)."""
    return u * 1000.0 / (rho * g)


def tensao_total(gamma, z):
    """σ = γ·z (kPa), tensão vertical total na profundidade z."""
    return gamma * z


def tensao_efetiva(sigma, u):
    """Princípio de Terzaghi: σ' = σ − u (kPa)."""
    return sigma - u


def razao_poropressao(u, gamma, z):
    """r_u = u / (γ·z): parcela da tensão total suportada pela água."""
    return u / (gamma * z)


def fator_seguranca_talude_infinito(u, gamma, z, beta_graus, c_ef, phi_graus):
    """Fator de segurança de talude infinito com poropressão (Mohr-Coulomb).

        FS = [c' + (γ·z·cos²β − u)·tan φ'] / (γ·z·sen β·cos β)

    Modelo simplificado, usado aqui apenas como indicador didático. Não
    substitui métodos de equilíbrio limite (Bishop, Spencer, Morgenstern-Price).
    """
    beta = math.radians(beta_graus)
    phi = math.radians(phi_graus)
    normal_efetiva = max(gamma * z * math.cos(beta) ** 2 - u, 0.0)
    resistencia = c_ef + normal_efetiva * math.tan(phi)
    solicitacao = gamma * z * math.sin(beta) * math.cos(beta)
    return resistencia / solicitacao


def pesos_especificos(gs, e, w, gamma_w=GAMMA_W):
    """Pesos específicos (kN/m³) a partir dos índices físicos: seco, natural e saturado."""
    seco = gs * gamma_w / (1 + e)
    return {"seco": seco, "natural": seco * (1 + w), "saturado": (gs + e) * gamma_w / (1 + e)}


def tensao_vertical(z, zw, gamma_acima, gamma_abaixo):
    """σv (kPa) na profundidade z: γ_acima até a linha freática (profundidade zw), γ_abaixo depois."""
    return gamma_acima * min(z, zw) + gamma_abaixo * max(z - zw, 0.0)


def fs_talude_infinito_geral(sigma_v, u, beta_graus, c_ef, phi_graus, kh=0.0):
    """Talude infinito para qualquer σv, com sismo pseudoestático (coeficiente kh).

        FS = [c' + (σv·(cos²β − kh·senβ·cosβ) − u)·tan φ'] / [σv·(senβ·cosβ + kh·cos²β)]

    Com kh = 0 e σv = γ·z é a mesma expressão de fator_seguranca_talude_infinito.
    """
    beta = math.radians(beta_graus)
    sen, cos = math.sin(beta), math.cos(beta)
    normal_efetiva = max(sigma_v * (cos * cos - kh * sen * cos) - u, 0.0)
    resistencia = c_ef + normal_efetiva * math.tan(math.radians(phi_graus))
    return resistencia / (sigma_v * (sen * cos + kh * cos * cos))


def varredura_profundidade(u_piezo, z_piezo, gamma_nat, gamma_sat, beta_graus, c_ef, phi_graus,
                           z_max, passo, kh=0.0, gamma_acima=None):
    """Menor FS entre as superfícies paralelas ao talude até z_max, com rᵤ constante.

    A linha freática fica à profundidade zw = z_piezo − u/γw (pressão hidrostática
    acima da ponta do piezômetro). O rᵤ medido na ponta define u em todas as
    profundidades. gamma_acima (maciço umedecido pela chuva) muda só o peso
    acima da linha freática; a poropressão continua a do piezômetro.
    """
    u_piezo = max(u_piezo, 0.0)
    zw = max(z_piezo - u_piezo / GAMMA_W, 0.0)
    ru = u_piezo / tensao_vertical(z_piezo, zw, gamma_nat, gamma_sat)
    gamma_acima = gamma_acima or gamma_nat
    melhor = None
    for i in range(1, int(round(z_max / passo)) + 1):
        z = i * passo
        u = ru * tensao_vertical(z, zw, gamma_nat, gamma_sat)
        sv = tensao_vertical(z, zw, gamma_acima, gamma_sat)
        fs = fs_talude_infinito_geral(sv, u, beta_graus, c_ef, phi_graus, kh)
        if melhor is None or fs < melhor["fs"]:
            melhor = {"fs": fs, "z": z, "sigma_v": sv, "u": u}
    return {**melhor, "ru": ru, "zw": zw}


def fs_rebaixamento_rapido(gamma_sat, beta_graus, c_ef, phi_graus, z_max, passo):
    """Menor FS do talude de montante logo após um rebaixamento rápido (talude infinito).

    O maciço continua saturado e a poropressão não dissipa: percolação paralela
    ao talude, u = γw·z·cos²β, já sem o empuxo da água do reservatório.
    """
    cos2 = math.cos(math.radians(beta_graus)) ** 2
    melhor = None
    for i in range(1, int(round(z_max / passo)) + 1):
        z = i * passo
        fs = fs_talude_infinito_geral(gamma_sat * z, GAMMA_W * z * cos2, beta_graus, c_ef, phi_graus)
        if melhor is None or fs < melhor["fs"]:
            melhor = {"fs": fs, "z": z}
    return melhor


def gradiente_hidraulico(carga_montante, carga_jusante, comprimento):
    """i = Δh / L (adimensional)."""
    return max(carga_montante - carga_jusante, 0.0) / comprimento


def gradiente_critico(gamma_sat, gamma_w=GAMMA_W):
    """i_cr = (γsat − γw) / γw: gradiente que anula a tensão efetiva na saída do fluxo."""
    return (gamma_sat - gamma_w) / gamma_w


def altura_onda(vento_kmh, pista_km, g=config.GRAVIDADE):
    """Altura significativa da onda de vento (m), pista limitada e águas profundas.

    SPM (1984): g·H/U² = 1,6×10⁻³·(g·F/U²)^½, ou seja, H = 1,6×10⁻³ · U · √(F/g).
    """
    u = max(vento_kmh, 0.0) / 3.6
    return 1.6e-3 * u * math.sqrt(pista_km * 1000.0 / g)


def sobrelevacao_vento(vento_kmh, pista_km, profundidade_m):
    """Sobrelevação do nível pelo vento (m), fórmula de Zuider Zee: S = V²·F / (62 000·D)."""
    if profundidade_m <= 0:
        return 0.0
    return max(vento_kmh, 0.0) ** 2 * pista_km / (62000.0 * profundidade_m)


def borda_livre_efetiva(cota_crista, recalque_mm, nivel, espraiamento, sobrelevacao):
    """BL_ef = (cota da crista − recalque) − nível − (espraiamento da onda + sobrelevação), em m."""
    return (cota_crista - recalque_mm / 1000.0) - nivel - (espraiamento + sobrelevacao)


def area_reservatorio(nivel, curva):
    """Área do espelho d'água (m²) interpolada na curva cota-área [(m, km²), ...]."""
    if nivel <= curva[0][0]:
        return curva[0][1] * 1e6
    for (h0, a0), (h1, a1) in zip(curva, curva[1:]):
        if nivel <= h1:
            return (a0 + (nivel - h0) / (h1 - h0) * (a1 - a0)) * 1e6
    (h0, a0), (h1, a1) = curva[-2], curva[-1]
    return (a1 + (nivel - h1) / (h1 - h0) * (a1 - a0)) * 1e6


def vazao_vertedouro(nivel, cota_soleira, largura, coef):
    """Vertedouro de soleira livre: Q = C·L·H^1,5 (m³/s), com H a carga sobre a soleira."""
    carga = nivel - cota_soleira
    return coef * largura * carga ** 1.5 if carga > 0 else 0.0


def prever_nivel(nivel, vazao_afluente, horas, nivel_galgamento, vazao_infiltracao=0.0,
                 res=config.RESERVATORIO, passo_s=300):
    """Balanço hídrico dV/dt = Q_afl − Q_vert − Q_tomada − Q_infiltr − E·A, com afluência constante.

    Integra A(h)·dh = dV passo a passo e devolve o nível máximo no horizonte e,
    se houver, as horas até o nível atingir nivel_galgamento.
    """
    h = h_max = nivel
    horas_galgamento = None
    for passo in range(1, int(horas * 3600 / passo_s) + 1):
        area = max(area_reservatorio(h, res["curva_cota_area"]), 1000.0)
        saida = (vazao_vertedouro(h, res["cota_soleira_vertedouro_m"], res["largura_vertedouro_m"],
                                  res["coef_descarga_vertedouro"])
                 + res["vazao_tomada_m3s"] + vazao_infiltracao
                 + res["evaporacao_mm_dia"] / 1000.0 * area / 86400.0)
        h = max(h + (vazao_afluente - saida) * passo_s / area, 0.0)
        h_max = max(h_max, h)
        if horas_galgamento is None and h >= nivel_galgamento:
            horas_galgamento = passo * passo_s / 3600.0
    return {"nivel_max": h_max, "nivel_final": h, "horas_ate_galgamento": horas_galgamento}


def confiabilidade(fs_de, c_ef, phi_graus, cv_c, cv_phi, amostras, semente=1):
    """Monte Carlo com c' e φ' normais (truncadas): probabilidade de FS < 1 e índice β.

    fs_de(c, phi) calcula o FS de uma amostra. A semente fixa deixa o resultado
    igual entre avaliações com as mesmas leituras.
    """
    rng = random.Random(semente)
    valores = []
    for _ in range(amostras):
        c = max(rng.gauss(c_ef, cv_c * c_ef), 0.0)
        phi = min(max(rng.gauss(phi_graus, cv_phi * phi_graus), 1.0), 60.0)
        valores.append(fs_de(c, phi))
    media = sum(valores) / amostras
    desvio = math.sqrt(sum((v - media) ** 2 for v in valores) / (amostras - 1))
    return {
        "media": media,
        "desvio": desvio,
        "prob_ruptura": sum(v < 1.0 for v in valores) / amostras,
        "beta": (media - 1.0) / desvio if desvio > 0 else None,
    }


# ---------------------------------------------------------------------------
# Normalização e classificação
# ---------------------------------------------------------------------------

def normalizar(valor, var):
    """Converte a leitura em uma nota de 0 a 1, linear por trechos.

    base -> 0,00 | atenção -> 0,25 | alerta -> 0,50 | crítico -> 0,75
    Acima do crítico continua com a inclinação do último trecho, até 1,00.
    """
    pontos = [(var.base, 0.0), (var.atencao, 0.25), (var.alerta, 0.50), (var.critico, 0.75)]
    if valor <= var.base:
        return 0.0
    for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
        if valor <= x1:
            return y0 + (valor - x0) / (x1 - x0) * (y1 - y0)
    excedente = (valor - var.critico) / (var.critico - var.alerta) * 0.25
    return min(0.75 + excedente, 1.0)


def classificar_valor(valor, var):
    if valor >= var.critico:
        return "Crítico"
    if valor >= var.alerta:
        return "Alerta"
    if valor >= var.atencao:
        return "Atenção"
    return "Normal"


def classificar_indice(indice):
    for limite, nivel in config.FAIXAS_INDICE:
        if indice < limite:
            return nivel
    return "Crítico"


def classificar_abaixo(valor, faixas):
    """Nível de um indicador em que menor é pior (FS, borda livre): faixas [(limite, nível), ...]."""
    for limite, nivel in faixas:
        if valor < limite:
            return nivel
    return "Normal"


def classificar_acima(valor, limites):
    """Nível de um indicador em que maior é pior: limites (atenção, alerta, crítico)."""
    for limite, nivel in zip(reversed(limites), ("Crítico", "Alerta", "Atenção")):
        if valor >= limite:
            return nivel
    return "Normal"


def classificar_fs(fs):
    return classificar_abaixo(fs, config.FAIXAS_FS)


# ---------------------------------------------------------------------------
# Modos de ruptura
# ---------------------------------------------------------------------------

NOMES_TAXA = {
    "pressao_poros": ("Taxa da pressão de poros", "kPa/dia"),
    "vazao_infiltracao": ("Taxa da vazão de infiltração", "(L/min)/dia"),
    "deslocamento_horizontal": ("Velocidade do deslocamento", "mm/dia"),
}


def _indicador(nome, valor, unidade="", nivel=None, detalhe="", casas=2, tendencia=False):
    """Indicador de um modo de ruptura. nivel=None marca um indicador só informativo;
    tendencia=True marca taxas e resíduos (estatísticos, sujeitos a ruído)."""
    return {"nome": nome, "valor": None if valor is None else round(valor, 4), "unidade": unidade,
            "nivel": nivel, "detalhe": detalhe, "casas": casas, "tendencia": tendencia}


def _texto(ind):
    if ind["valor"] is None:
        return ""
    return f" {br(ind['valor'], ind['casas'])}{' ' + ind['unidade'] if ind['unidade'] else ''}"


def _tendencias(ctx, chave):
    """Taxa de variação e resíduo do modelo de valor esperado de uma variável."""
    indicadores = []
    taxa = ctx.get("taxas", {}).get(chave)
    if taxa is not None:
        nome, unidade = NOMES_TAXA[chave]
        indicadores.append(_indicador(nome, taxa, unidade, classificar_acima(taxa, config.LIMITES_TAXA[chave]),
                                      f"regressão nas últimas {config.TENDENCIAS['janela_taxa_h']} h", tendencia=True))
    r = ctx.get("residuos", {}).get(chave)
    if r:
        var = config.VARIAVEIS[chave]
        indicadores.append(_indicador(
            f"{var.nome} acima do esperado", r["z"], "σ", classificar_acima(r["z"], config.LIMITES_RESIDUO_Z),
            f"medido {br(r['medido'])} · esperado {br(r['previsto'])} ± {br(r['desvio'])} {var.unidade} "
            f"(modelo com {r['pontos']} h de histórico)", casas=1, tendencia=True))
    return indicadores


def _gamma_acima(pesos, api_mm):
    """γ acima da linha freática: vai do natural ao saturado conforme a chuva antecedente."""
    if not api_mm:
        return pesos["natural"]
    s = min(api_mm / config.MACICO["api_saturacao_mm"], 1.0)
    return pesos["natural"] + s * (pesos["saturado"] - pesos["natural"])


def _modo_galgamento(leit):
    nivel = leit.get("nivel_reservatorio")
    if nivel is None:
        return []
    res, geo = config.RESERVATORIO, config.GEOMETRIA
    recalque = max(leit.get("recalque", 0.0), 0.0)
    crista = geo["cota_crista_m"] - recalque / 1000.0
    vento = leit.get("vento")
    onda = res["coef_espraiamento"] * altura_onda(vento, res["pista_vento_km"]) if vento is not None else 0.0
    sobre = (sobrelevacao_vento(vento, res["pista_vento_km"], nivel * res["fracao_profundidade_media"])
             if vento is not None else 0.0)
    bl = borda_livre_efetiva(geo["cota_crista_m"], recalque, nivel, onda, sobre)
    indicadores = [_indicador(
        "Borda livre efetiva", bl, "m", classificar_abaixo(bl, config.FAIXAS_BORDA_LIVRE),
        f"crista {br(crista, 3)} m − nível {br(nivel)} m − onda {br(onda)} m − sobrelevação {br(sobre, 3)} m")]

    q_afl = leit.get("vazao_afluente")
    if q_afl is not None:
        q_inf = max(leit.get("vazao_infiltracao", 0.0), 0.0) / 60000.0   # L/min -> m³/s
        horas = res["horizonte_previsao_h"]
        prev = prever_nivel(nivel, q_afl, horas, crista - onda - sobre, q_inf)
        bl_prev = crista - prev["nivel_max"] - onda - sobre
        quando = (f"galgamento em {br(prev['horas_ate_galgamento'], 1)} h"
                  if prev["horas_ate_galgamento"] is not None else "sem galgamento")
        indicadores.append(_indicador(
            f"Borda livre prevista ({horas} h)", bl_prev, "m", classificar_abaixo(bl_prev, config.FAIXAS_BORDA_LIVRE),
            f"balanço hídrico com afluência de {br(q_afl, 1)} m³/s: nível máximo {br(prev['nivel_max'])} m; {quando}"))
    return indicadores


def _modo_erosao_interna(leit, ctx, pesos):
    indicadores = []
    geo = config.GEOMETRIA
    u = leit.get("pressao_poros")
    if u is not None:
        carga = geo["cota_ponta_piezometro_m"] + max(u, 0.0) / GAMMA_W
        i = gradiente_hidraulico(carga, geo["cota_saida_m"], geo["distancia_piezometro_saida_m"])
        i_cr = gradiente_critico(pesos["saturado"])
        if i > 0:
            fs = i_cr / i
            indicadores.append(_indicador(
                "FS contra piping", fs, "", classificar_abaixo(fs, config.FAIXAS_FS_PIPING),
                f"gradiente i = {br(i, 3)} (carga de {br(carga)} m em {br(geo['distancia_piezometro_saida_m'], 0)} m "
                f"até o dreno); i_cr = {br(i_cr, 2)}"))
    tendencias = _tendencias(ctx, "vazao_infiltracao")
    indicadores += tendencias

    turbidez = leit.get("turbidez")
    if turbidez is not None:
        nivel_turbidez = classificar_valor(turbidez, config.VARIAVEIS["turbidez"])
        indicadores.append(_indicador("Turbidez da drenagem", turbidez, "NTU", None,
                                      f"nível da variável: {nivel_turbidez}", casas=1))
        # Água turva junto com vazão crescente ou acima do esperado: carreamento de solo.
        vazao = leit.get("vazao_infiltracao")
        vazao_alta = any(ind["nivel"] not in (None, "Normal") for ind in tendencias) or (
            vazao is not None and classificar_valor(vazao, config.VARIAVEIS["vazao_infiltracao"]) != "Normal")
        if nivel_turbidez != "Normal" and vazao_alta:
            indicadores.append(_indicador(
                "Água turva com vazão elevada", None, "",
                "Crítico" if nivel_turbidez in ("Alerta", "Crítico") else "Alerta",
                "carreamento de solo junto com aumento da percolação: indício forte de piping"))
    return indicadores


def _modo_talude_jusante(leit, ctx, pesos, geo):
    u = leit.get("pressao_poros")
    if u is None:
        return [], None
    g_acima = _gamma_acima(pesos, ctx.get("api_mm"))
    args = (geo["inclinacao_talude_graus"], geo["coesao_efetiva"], geo["angulo_atrito_graus"])
    v = varredura_profundidade(u, geo["profundidade_ruptura"], pesos["natural"], pesos["saturado"], *args,
                               geo["profundidade_max_ruptura"], geo["passo_varredura"], gamma_acima=g_acima)
    sigma_piezo = tensao_vertical(geo["profundidade_ruptura"], v["zw"], g_acima, pesos["saturado"])
    fs_piezo = fs_talude_infinito_geral(sigma_piezo, max(u, 0.0), *args)
    conf = confiabilidade(
        lambda c, phi: fs_talude_infinito_geral(v["sigma_v"], v["u"], geo["inclinacao_talude_graus"], c, phi),
        geo["coesao_efetiva"], geo["angulo_atrito_graus"], geo["cv_coesao"], geo["cv_atrito"],
        geo["amostras_monte_carlo"])
    indicadores = [
        _indicador("FS mínimo (varredura de profundidade)", v["fs"], "", classificar_fs(v["fs"]),
                   f"superfície crítica a {br(v['z'])} m; rᵤ = {br(v['ru'], 3)}; γ acima da linha freática "
                   f"{br(g_acima, 1)} kN/m³ e abaixo {br(pesos['saturado'], 1)} kN/m³"),
        _indicador(f"FS a {br(geo['profundidade_ruptura'], 0)} m (ponta do piezômetro)", fs_piezo, "", None,
                   "mesma superfície do modelo original"),
    ]
    if conf["beta"] is not None:
        indicadores.append(_indicador(
            "Índice de confiabilidade β", conf["beta"], "", None,
            f"P(FS < 1) = {br(conf['prob_ruptura'] * 100, 1)}% (Monte Carlo com {geo['amostras_monte_carlo']} "
            f"amostras; CV de c' {br(geo['cv_coesao'] * 100, 0)}% e de φ' {br(geo['cv_atrito'] * 100, 0)}%)"))
    return indicadores + _tendencias(ctx, "pressao_poros"), {**v, "g_acima": g_acima, "sigma_piezo": sigma_piezo}


def _modo_talude_montante(ctx, pesos, geo):
    taxa = ctx.get("taxas", {}).get("nivel_reservatorio")
    if taxa is None:
        return []
    limiar = config.RESERVATORIO["limiar_rebaixamento_m_dia"]
    if taxa > -limiar:
        return [_indicador("Variação do nível", taxa, "m/dia", None, "sem rebaixamento rápido")]
    r = fs_rebaixamento_rapido(pesos["saturado"], geo["inclinacao_talude_montante_graus"], geo["coesao_efetiva"],
                               geo["angulo_atrito_graus"], geo["profundidade_max_ruptura"], geo["passo_varredura"])
    return [
        _indicador("Variação do nível", taxa, "m/dia", None, f"rebaixamento mais rápido que {br(limiar, 1)} m/dia"),
        _indicador("FS de montante (rebaixamento rápido)", r["fs"], "",
                   classificar_abaixo(r["fs"], config.FAIXAS_FS_REBAIXAMENTO),
                   f"maciço ainda saturado, sem dissipar a poropressão; superfície crítica a {br(r['z'])} m"),
    ]


def _modo_sismico(leit, pesos, geo, g_acima):
    pga = leit.get("vibracao")
    if pga is None:
        return []
    s = config.SISMO
    if pga < s["pga_minima_g"]:
        return [_indicador("Aceleração de pico", pga, "g", None,
                           f"abaixo de {br(s['pga_minima_g'])} g: sem evento a verificar", casas=3)]
    kh = s["fracao_pga_kh"] * pga
    f = s["fator_resistencia"]
    phi_reduzido = math.degrees(math.atan(f * math.tan(math.radians(geo["angulo_atrito_graus"]))))
    v = varredura_profundidade(leit.get("pressao_poros", 0.0), geo["profundidade_ruptura"], pesos["natural"],
                               pesos["saturado"], geo["inclinacao_talude_graus"], f * geo["coesao_efetiva"],
                               phi_reduzido, geo["profundidade_max_ruptura"], geo["passo_varredura"], kh,
                               gamma_acima=g_acima)
    return [
        _indicador("Aceleração de pico", pga, "g", None, f"kh = {br(s['fracao_pga_kh'], 1)} · PGA = {br(kh, 3)}", casas=3),
        _indicador("FS pseudoestático", v["fs"], "", classificar_abaixo(v["fs"], config.FAIXAS_FS_SISMICO),
                   f"c' e tan φ' reduzidos a {br(f * 100, 0)}%; superfície crítica a {br(v['z'])} m"),
    ]


def _modo_deformacoes(ctx):
    indicadores = _tendencias(ctx, "deslocamento_horizontal")
    fk = ctx.get("fukuzono")
    if fk:
        quando = ("a reta de 1/v já chegou a zero: ruptura iminente" if fk["horas"] == 0
                  else "velocidade inversa caindo")
        indicadores.append(_indicador(
            "Tempo até a ruptura (Fukuzono)", fk["horas"], "h", classificar_abaixo(fk["horas"], config.FAIXAS_FUKUZONO_H),
            f"{quando}; velocidade atual {br(fk['velocidade'], 1)} mm/dia", casas=0))
    return indicadores


def _modo(chave, nome, indicadores):
    """Nível do modo: o mais severo entre os indicadores.

    Como na regra das variáveis críticas, uma tendência (taxa ou resíduo) sozinha
    leva o modo no máximo a Alerta; para Crítico, outro indicador do mesmo modo
    precisa estar acima de Normal. Sem indicadores o nível é None (sem dados);
    só com informativos (ex.: sem evento sísmico), Normal.
    """
    fisico = nivel_max(*(i["nivel"] for i in indicadores if not i["tendencia"]))
    tendencia = nivel_max(*(i["nivel"] for i in indicadores if i["tendencia"]))
    limitado = tendencia == "Crítico" and fisico in (None, "Normal")
    nivel = nivel_max(fisico, "Alerta" if limitado else tendencia) or ("Normal" if indicadores else None)
    return {"chave": chave, "nome": nome, "nivel": nivel, "limitado": limitado, "indicadores": indicadores}


# ---------------------------------------------------------------------------
# Avaliação
# ---------------------------------------------------------------------------

def avaliar(leituras, variaveis=None, geotecnia=None, contexto=None):
    """Avalia um conjunto de leituras {chave: valor}.

    Retorna a classificação de cada variável, o índice de risco ponderado, o
    fator de segurança, as grandezas derivadas, os modos de ruptura e o nível
    global, com os motivos que levaram a ele. O contexto (opcional) traz o que
    depende do histórico: taxas, chuva antecedente, resíduos e Fukuzono
    (ver monitor/tendencias.py).
    """
    variaveis = variaveis or config.VARIAVEIS
    geo = geotecnia or config.GEOTECNIA
    ctx = contexto or {}

    por_variavel = {}
    soma_pesos = 0.0
    soma_ponderada = 0.0
    for chave, valor in leituras.items():
        var = variaveis.get(chave)
        if var is None or valor is None:
            continue
        nota = normalizar(valor, var)
        por_variavel[chave] = {
            "valor": valor,
            "unidade": var.unidade,
            "nota": round(nota, 4),
            "nivel": classificar_valor(valor, var),
            "peso": var.peso,
        }
        if var.peso > 0:
            soma_pesos += var.peso
            soma_ponderada += var.peso * nota

    # Se algum sensor do índice estiver sem leitura, os pesos restantes são
    # reescalados para continuar somando 100%. A cobertura fica registrada.
    indice = soma_ponderada / soma_pesos if soma_pesos else 0.0
    total_pesos = sum(v.peso for v in variaveis.values())
    cobertura = soma_pesos / total_pesos if total_pesos else 0.0

    motivos = []
    nivel_indice = classificar_indice(indice)
    nivel = nivel_indice
    motivos.append(f"Índice de risco {br(indice)} → {nivel_indice}")

    # Regra de sobreposição: a média ponderada não pode "esconder" uma
    # variável crítica isolada.
    criticas = [variaveis[c].nome for c, d in por_variavel.items() if d["nivel"] == "Crítico"]
    if len(criticas) >= 2:
        nivel = nivel_max(nivel, "Crítico")
        motivos.append(f"Duas ou mais variáveis críticas ({', '.join(criticas)}) → Crítico")
    elif len(criticas) == 1:
        nivel = nivel_max(nivel, "Alerta")
        motivos.append(f"Variável crítica ({criticas[0]}) → no mínimo Alerta")

    # Modos de ruptura: cada um combina leituras de vários sensores (e o
    # histórico) em indicadores próprios. O nível global é o mais severo.
    m = config.MACICO
    pesos = pesos_especificos(m["densidade_graos"], m["indice_vazios"], m["umidade"])
    leit = {k: v for k, v in leituras.items() if v is not None}
    ind_jusante, varredura = _modo_talude_jusante(leit, ctx, pesos, geo)
    g_acima = varredura["g_acima"] if varredura else _gamma_acima(pesos, ctx.get("api_mm"))
    modos = [
        _modo("galgamento", "Galgamento", _modo_galgamento(leit)),
        _modo("erosao_interna", "Erosão interna (piping)", _modo_erosao_interna(leit, ctx, pesos)),
        _modo("talude_jusante", "Talude de jusante", ind_jusante),
        _modo("talude_montante", "Talude de montante", _modo_talude_montante(ctx, pesos, geo)),
        _modo("sismico", "Sismo", _modo_sismico(leit, pesos, geo, g_acima)),
        _modo("deformacoes", "Deformações", _modo_deformacoes(ctx)),
    ]
    for modo in modos:
        for ind in modo["indicadores"]:
            if ind["nivel"] not in (None, "Normal"):
                motivos.append(f"{modo['nome']}: {ind['nome']}{_texto(ind)} → {ind['nivel']}")
        if modo["limitado"]:
            motivos.append(f"{modo['nome']}: tendência crítica sem confirmação de outro indicador → Alerta")
        nivel = nivel_max(nivel, modo["nivel"])

    derivados = {}
    if "nivel_reservatorio" in leit:
        derivados["pressao_hidrostatica_base_kpa"] = round(pressao_hidrostatica(leit["nivel_reservatorio"]), 2)
    if varredura:
        u = leit["pressao_poros"]
        derivados["carga_piezometrica_m"] = round(carga_piezometrica(u), 3)
        derivados["tensao_total_kpa"] = round(varredura["sigma_piezo"], 2)
        derivados["tensao_efetiva_kpa"] = round(tensao_efetiva(varredura["sigma_piezo"], u), 2)
        derivados["razao_poropressao_ru"] = round(varredura["ru"], 3)
    if ctx.get("api_mm") is not None:
        derivados["chuva_antecedente_mm"] = round(ctx["api_mm"], 1)

    return {
        "indice": round(indice, 4),
        "nivel_indice": nivel_indice,
        "cobertura": round(cobertura, 4),
        "fator_seguranca": round(varredura["fs"], 3) if varredura else None,
        "nivel": nivel,
        "motivos": motivos,
        "variaveis": por_variavel,
        "derivados": derivados,
        "modos": modos,
    }
