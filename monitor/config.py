"""Parâmetros do sistema de monitoramento.

ATENÇÃO: todos os limites, pesos e parâmetros geotécnicos abaixo são
EXPERIMENTAIS e ILUSTRATIVOS, definidos para uma barragem de terra fictícia
de ~15 m de altura usada no protótipo. Eles fazem parte da metodologia do
projeto acadêmico e NÃO são valores normativos de engenharia. Em uma barragem
real, os limites de controle de cada instrumento são definidos pelo projetista
/ responsável técnico, a partir do projeto, do histórico de leituras e das
análises de estabilidade (ver docs/03-metodologia-analise.md).
"""

from dataclasses import dataclass

# Níveis de classificação, em ordem crescente de severidade.
NIVEIS = ["Normal", "Atenção", "Alerta", "Crítico"]


@dataclass(frozen=True)
class Variavel:
    chave: str
    nome: str
    unidade: str
    equipamento: str
    # Limites de controle (valores crescentes): referência, atenção, alerta, crítico.
    base: float
    atencao: float
    alerta: float
    critico: float
    # Peso no índice de risco (0 = variável monitorada, mas fora do índice).
    peso: float = 0.0
    descricao: str = ""


VARIAVEIS = {
    v.chave: v
    for v in [
        Variavel(
            "nivel_reservatorio", "Nível do reservatório", "m", "Sensor de nível",
            base=10.0, atencao=12.0, alerta=13.0, critico=14.0, peso=0.15,
            descricao="Carga hidráulica sobre a estrutura (crista a 15 m).",
        ),
        Variavel(
            "pressao_poros", "Pressão de poros", "kPa", "Piezômetro",
            base=15.0, atencao=25.0, alerta=35.0, critico=45.0, peso=0.25,
            descricao="Pressão da água nos poros do maciço, no talude de jusante.",
        ),
        Variavel(
            "vazao_infiltracao", "Vazão de infiltração", "L/min", "Medidor de vazão",
            base=20.0, atencao=35.0, alerta=50.0, critico=70.0, peso=0.20,
            descricao="Vazão de percolação coletada no dreno de pé.",
        ),
        Variavel(
            "deslocamento_horizontal", "Deslocamento horizontal", "mm", "Inclinômetro",
            base=5.0, atencao=15.0, alerta=25.0, critico=40.0, peso=0.20,
            descricao="Deslocamento horizontal acumulado do talude.",
        ),
        Variavel(
            "recalque", "Recalque", "mm", "Marco / medidor de recalque",
            base=10.0, atencao=25.0, alerta=40.0, critico=60.0, peso=0.10,
            descricao="Deslocamento vertical acumulado da crista.",
        ),
        Variavel(
            "chuva_24h", "Chuva acumulada (24 h)", "mm", "Pluviômetro",
            base=10.0, atencao=50.0, alerta=80.0, critico=120.0, peso=0.05,
            descricao="Precipitação acumulada nas últimas 24 horas.",
        ),
        Variavel(
            "inclinacao", "Variação de inclinação", "°", "Inclinômetro / tiltímetro",
            base=0.1, atencao=0.5, alerta=1.0, critico=2.0, peso=0.05,
            descricao="Variação angular em relação à leitura inicial.",
        ),
        Variavel(
            "vibracao", "Aceleração de pico", "g", "Acelerômetro",
            base=0.01, atencao=0.05, alerta=0.10, critico=0.20, peso=0.0,
            descricao="Evento sísmico/vibração. Fora do índice; gera alertas próprios.",
        ),
        Variavel(
            "temperatura", "Temperatura", "°C", "Termômetro",
            base=30.0, atencao=40.0, alerta=50.0, critico=60.0, peso=0.0,
            descricao="Temperatura ambiente/sensores. Usada para contexto e diagnóstico.",
        ),
        Variavel(
            "turbidez", "Turbidez da drenagem", "NTU", "Turbidímetro",
            base=5.0, atencao=20.0, alerta=50.0, critico=100.0, peso=0.0,
            descricao="Água turva no dreno de pé indica carreamento de solo (erosão interna).",
        ),
        Variavel(
            "vento", "Velocidade do vento", "km/h", "Anemômetro",
            base=15.0, atencao=40.0, alerta=60.0, critico=80.0, peso=0.0,
            descricao="Gera ondas e sobrelevação do reservatório, que reduzem a borda livre.",
        ),
        Variavel(
            "vazao_afluente", "Vazão afluente", "m³/s", "Estação fluviométrica / previsão",
            base=5.0, atencao=20.0, alerta=40.0, critico=70.0, peso=0.0,
            descricao="Vazão que chega ao reservatório; alimenta o balanço hídrico.",
        ),
    ]
}

# Faixas do índice de risco (0 a 1). Coincidem com a normalização das
# variáveis: atenção -> 0,25; alerta -> 0,50; crítico -> 0,75.
FAIXAS_INDICE = [(0.25, "Normal"), (0.50, "Atenção"), (0.75, "Alerta")]  # >= 0,75: Crítico

# Faixas do fator de segurança (FS). Abaixo de cada valor, o nível indicado.
# Referência: FS mínimo usual de 1,5 para percolação permanente.
FAIXAS_FS = [(1.1, "Crítico"), (1.3, "Alerta"), (1.5, "Atenção")]

DENSIDADE_AGUA = 1000.0   # ρ (kg/m³)
GRAVIDADE = 9.81          # g (m/s²)
GAMMA_W = DENSIDADE_AGUA * GRAVIDADE / 1000.0   # γw (kN/m³)

# Índices físicos do maciço compactado (ensaios de laboratório). Os pesos
# específicos saem deles: γd = Gs·γw/(1+e), γsat = (Gs+e)·γw/(1+e), γnat = γd·(1+w).
MACICO = {
    "densidade_graos": 2.70,       # Gs
    "indice_vazios": 0.60,         # e
    "umidade": 0.15,               # w da zona não saturada
    "api_saturacao_mm": 150.0,     # chuva antecedente que satura a zona acima da linha freática
}

# Parâmetros geotécnicos dos taludes (modelo de talude infinito).
GEOTECNIA = {
    "profundidade_ruptura": 5.0,       # profundidade da ponta do piezômetro (m)
    "inclinacao_talude_graus": 21.8,   # β de jusante (°), talude 1V:2,5H
    "inclinacao_talude_montante_graus": 18.4,  # β de montante (°), talude 1V:3H
    "coesao_efetiva": 15.0,            # c' (kPa)
    "angulo_atrito_graus": 32.0,       # φ' (°)
    "profundidade_max_ruptura": 8.0,   # varredura de z até aqui (altura do talude no piezômetro)
    "passo_varredura": 0.25,           # m
    "cv_coesao": 0.20,                 # coeficientes de variação para o Monte Carlo
    "cv_atrito": 0.10,
    "amostras_monte_carlo": 2000,
}

# Geometria usada no gradiente de saída e na borda livre (cotas a partir do pé da barragem).
GEOMETRIA = {
    "cota_crista_m": 15.0,
    "cota_ponta_piezometro_m": 3.0,          # ponta 5 m abaixo do talude de jusante
    "distancia_piezometro_saida_m": 20.0,    # caminho de fluxo até o dreno de pé
    "cota_saida_m": 0.0,                     # dreno de pé
}

# Reservatório: ondas de vento, vertedouro e curva cota-área do balanço hídrico.
RESERVATORIO = {
    "pista_vento_km": 1.5,                   # fetch
    "fracao_profundidade_media": 0.5,        # profundidade média / nível, na sobrelevação
    "coef_espraiamento": 1.5,                # espraiamento R = coef × altura da onda
    "cota_soleira_vertedouro_m": 12.0,
    "largura_vertedouro_m": 8.0,
    "coef_descarga_vertedouro": 2.0,         # Q = C·L·H^1,5 (SI)
    "vazao_tomada_m3s": 4.0,                 # descarga operacional constante
    "evaporacao_mm_dia": 5.0,
    "horizonte_previsao_h": 24,
    "limiar_rebaixamento_m_dia": 0.5,        # rebaixamento mais rápido que isso é "rápido"
    # (cota em m, área do espelho d'água em km²)
    "curva_cota_area": [(0, 0.0), (4, 0.05), (8, 0.18), (10, 0.30), (12, 0.42),
                        (14, 0.56), (15, 0.64), (16, 0.72)],
}

# Verificação pseudoestática (critério de Hynes-Griffin e Franklin).
SISMO = {
    "fracao_pga_kh": 0.5,      # kh = 0,5 · PGA/g
    "fator_resistencia": 0.8,  # c' e tan φ' reduzidos em 20%
    "pga_minima_g": 0.05,      # abaixo disso não há evento a verificar
}

# Faixas dos indicadores dos modos de ruptura: abaixo de cada valor, o nível indicado.
FAIXAS_FS_SISMICO = [(1.0, "Crítico"), (1.05, "Alerta"), (1.1, "Atenção")]
FAIXAS_FS_REBAIXAMENTO = [(1.0, "Crítico"), (1.1, "Alerta"), (1.3, "Atenção")]
FAIXAS_FS_PIPING = [(1.5, "Crítico"), (2.0, "Alerta"), (3.0, "Atenção")]
FAIXAS_BORDA_LIVRE = [(0.5, "Crítico"), (1.0, "Alerta"), (2.0, "Atenção")]       # m
FAIXAS_FUKUZONO_H = [(24, "Crítico"), (72, "Alerta"), (168, "Atenção")]          # horas até a ruptura

# Limites crescentes (atenção, alerta, crítico) das taxas de variação e dos resíduos.
LIMITES_TAXA = {
    "deslocamento_horizontal": (1.0, 3.0, 10.0),   # mm/dia
    "pressao_poros": (3.0, 6.0, 10.0),             # kPa/dia
    "vazao_infiltracao": (5.0, 10.0, 20.0),        # (L/min)/dia
}
LIMITES_RESIDUO_Z = (2.0, 3.0, 4.0)   # desvios-padrão acima do valor esperado

# Séries temporais (médias horárias do banco).
TENDENCIAS = {
    "janela_taxa_h": 24,
    "min_horas_taxa": 6,
    "api_k": 0.9,                 # decaimento diário da chuva antecedente
    "api_dias": 30,
    "janela_modelo_dias": 30,     # treino dos modelos de valor esperado
    "excluir_recentes_h": 6,      # o treino não usa as últimas horas
    "min_pontos_modelo": 48,
    "fukuzono_janela_h": 72,
    "fukuzono_passo_h": 6,
    "fukuzono_v_min": 0.5,        # mm/dia
}

# Modelos de valor esperado: variáveis explicativas e desvio mínimo do resíduo.
# "api" é a chuva antecedente e "tempo" são os dias desde o início do treino.
MODELOS_RESIDUO = {
    "pressao_poros": {"variaveis": ["nivel_reservatorio", "api"], "piso_desvio": 1.0},
    "vazao_infiltracao": {"variaveis": ["nivel_reservatorio"], "piso_desvio": 2.0},
    "deslocamento_horizontal": {"variaveis": ["nivel_reservatorio", "temperatura", "tempo"], "piso_desvio": 0.5},
}
