"""Fórmulas e modelo de classificação/alerta.

Funções puras (sem banco de dados nem rede), para facilitar testes e o
estudo da metodologia. Detalhes em docs/03-metodologia-analise.md.
"""

import math

from . import config
from .config import NIVEIS


def br(numero, casas=2):
    """Formata um número com vírgula decimal (padrão brasileiro)."""
    return f"{numero:.{casas}f}".replace(".", ",")


def nivel_max(*niveis):
    """Retorna o nível mais severo entre os informados."""
    return max(niveis, key=NIVEIS.index)


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


def classificar_fs(fs):
    for limite, nivel in config.FAIXAS_FS:
        if fs < limite:
            return nivel
    return "Normal"


def avaliar(leituras, variaveis=None, geotecnia=None):
    """Avalia um conjunto de leituras {chave: valor}.

    Retorna um dicionário com a classificação de cada variável, o índice de
    risco ponderado, o fator de segurança, as grandezas derivadas e o nível
    global, com os motivos que levaram a ele.
    """
    variaveis = variaveis or config.VARIAVEIS
    geo = geotecnia or config.GEOTECNIA

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

    derivados = {}
    fs = None
    if "nivel_reservatorio" in leituras and leituras["nivel_reservatorio"] is not None:
        derivados["pressao_hidrostatica_base_kpa"] = round(
            pressao_hidrostatica(leituras["nivel_reservatorio"]), 2)
    u = leituras.get("pressao_poros")
    if u is not None:
        gamma, z = geo["peso_especifico_solo"], geo["profundidade_ruptura"]
        sigma = tensao_total(gamma, z)
        derivados["carga_piezometrica_m"] = round(carga_piezometrica(u), 3)
        derivados["tensao_total_kpa"] = round(sigma, 2)
        derivados["tensao_efetiva_kpa"] = round(tensao_efetiva(sigma, u), 2)
        derivados["razao_poropressao_ru"] = round(razao_poropressao(u, gamma, z), 3)
        fs = fator_seguranca_talude_infinito(
            u, gamma, z, geo["inclinacao_talude_graus"],
            geo["coesao_efetiva"], geo["angulo_atrito_graus"])
        nivel_fs = classificar_fs(fs)
        if NIVEIS.index(nivel_fs) > NIVEIS.index(nivel):
            motivos.append(f"Fator de segurança {br(fs)} → {nivel_fs}")
        nivel = nivel_max(nivel, nivel_fs)

    return {
        "indice": round(indice, 4),
        "nivel_indice": nivel_indice,
        "cobertura": round(cobertura, 4),
        "fator_seguranca": round(fs, 3) if fs is not None else None,
        "nivel": nivel,
        "motivos": motivos,
        "variaveis": por_variavel,
        "derivados": derivados,
    }
