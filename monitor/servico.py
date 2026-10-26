"""Regras de negócio: recebe leituras, avalia e gera alertas."""

import logging
from datetime import datetime, timedelta, timezone

from . import analise, config, tendencias
from .config import NIVEIS

log = logging.getLogger("monitor")

# Variáveis cujo histórico entra nas taxas, na chuva antecedente e nos modelos.
VARIAVEIS_HISTORICO = ("nivel_reservatorio", "pressao_poros", "vazao_infiltracao",
                       "deslocamento_horizontal", "chuva_24h", "temperatura")


class ErroValidacao(ValueError):
    pass


def agora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalizar_instante(texto):
    if texto is None:
        return agora_iso()
    try:
        dt = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError as e:
        raise ErroValidacao(f"Instante inválido: {texto!r}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validar_pacote(pacote):
    """Valida o JSON enviado pela estação de aquisição.

    Formato esperado:
        {"estacao": "EST-01", "instante": "2026-10-14T12:00:00Z" (opcional),
         "leituras": {"nivel_reservatorio": 10.4, "pressao_poros": 18.2, ...}}
    """
    if not isinstance(pacote, dict):
        raise ErroValidacao("O corpo deve ser um objeto JSON.")
    estacao = pacote.get("estacao") or "EST-01"
    leituras = pacote.get("leituras")
    if not isinstance(leituras, dict) or not leituras:
        raise ErroValidacao("Campo 'leituras' deve ser um objeto não vazio.")
    limpas = {}
    for chave, valor in leituras.items():
        if chave not in config.VARIAVEIS:
            raise ErroValidacao(f"Variável desconhecida: {chave!r}")
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ErroValidacao(f"Valor não numérico para {chave!r}")
        if valor != valor or valor in (float("inf"), float("-inf")):
            raise ErroValidacao(f"Valor inválido para {chave!r}")
        limpas[chave] = float(valor)
    return str(estacao), normalizar_instante(pacote.get("instante")), limpas


class Monitor:
    def __init__(self, banco):
        self.banco = banco

    def registrar(self, pacote):
        estacao, instante, leituras = validar_pacote(pacote)
        anterior = self.banco.ultima_avaliacao()
        self.banco.inserir_leituras(estacao, instante, leituras)

        # A avaliação usa a última leitura conhecida de cada sensor, pois nem
        # todos os sensores precisam enviar dados no mesmo pacote.
        atuais = {k: d["valor"] for k, d in self.banco.ultimas_leituras().items()}
        resultado = analise.avaliar(atuais, contexto=self.contexto(instante, atuais))
        self.banco.inserir_avaliacao(instante, resultado)
        alertas = self._gerar_alertas(instante, anterior, resultado)
        return {"instante": instante, "avaliacao": resultado, "alertas_gerados": alertas}

    def simular(self, pacote):
        """Avalia um pacote sem gravar nada (prévia da página de sensores).

        Segue a mesma regra de registrar: variáveis ausentes no pacote ficam
        com a última leitura conhecida.
        """
        _, instante, leituras = validar_pacote(pacote)
        atuais = {k: d["valor"] for k, d in self.banco.ultimas_leituras().items()}
        atuais.update(leituras)
        return analise.avaliar(atuais, contexto=self.contexto(instante, atuais))

    def contexto(self, instante, atuais):
        """Indicadores que dependem do histórico (médias horárias anteriores a 'instante').

        O valor atual de cada variável entra como último ponto das séries.
        """
        cfg = config.TENDENCIAS
        fim = datetime.fromisoformat(instante.replace("Z", "+00:00"))
        agora = fim.timestamp()
        dias = cfg["janela_modelo_dias"] + cfg["api_dias"]   # o API de cada ponto de treino olha mais 30 dias
        desde = (fim - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
        series = self.banco.series_horarias(VARIAVEIS_HISTORICO, desde, instante)
        com_atual = {k: s + [(agora, atuais[k])] if k in atuais else s for k, s in series.items()}

        taxas = {}
        for k in ("nivel_reservatorio", "pressao_poros", "vazao_infiltracao", "deslocamento_horizontal"):
            taxa = tendencias.taxa_diaria(com_atual[k], agora, cfg["janela_taxa_h"], cfg["min_horas_taxa"])
            if taxa is not None:
                taxas[k] = taxa
        api = tendencias.chuva_antecedente(com_atual["chuva_24h"], agora, cfg["api_k"], cfg["api_dias"])
        fukuzono = tendencias.velocidade_inversa(com_atual["deslocamento_horizontal"], agora,
                                                 cfg["fukuzono_janela_h"], cfg["fukuzono_passo_h"],
                                                 cfg["fukuzono_v_min"])
        explicativas = {**atuais, "api": api}
        residuos = {}
        for alvo, modelo in config.MODELOS_RESIDUO.items():
            r = tendencias.modelo_esperado(series, alvo, modelo["variaveis"], agora, explicativas, cfg,
                                           modelo["piso_desvio"])
            if r:
                residuos[alvo] = r
        return {"taxas": taxas, "api_mm": api, "fukuzono": fukuzono, "residuos": residuos}

    def _gerar_alertas(self, instante, anterior, atual):
        """Gera um alerta quando uma variável ou o nível global sobe de nível.

        Para evitar alertas repetidos quando uma leitura oscila em torno de um
        limite, o alerta não é gerado se já existir, para a mesma origem, um
        alerta pendente (não reconhecido) de nível igual ou superior.
        """
        gerados = []
        pendentes = self.banco.niveis_pendentes()
        niveis_antes = {}
        if anterior:
            niveis_antes = {k: d["nivel"] for k, d in anterior["variaveis"].items()}
            niveis_antes["global"] = anterior["nivel"]

        for chave, dados in atual["variaveis"].items():
            antes = niveis_antes.get(chave, "Normal")
            if self._deve_alertar(dados["nivel"], antes, pendentes.get(chave)):
                var = config.VARIAVEIS[chave]
                msg = (f"{var.nome}: {str(round(dados['valor'], 3)).replace('.', ',')} {var.unidade} "
                       f"({antes} → {dados['nivel']})")
                gerados.append(self._alertar(instante, chave, dados["nivel"], antes, dados["valor"], msg))

        # Modos de ruptura: origem "modo:<chave>".
        modos_antes = {m["chave"]: m["nivel"] for m in (anterior or {}).get("modos", []) if m["nivel"]}
        for modo in atual.get("modos", []):
            if not modo["nivel"]:
                continue
            origem = f"modo:{modo['chave']}"
            antes = modos_antes.get(modo["chave"], "Normal")
            if self._deve_alertar(modo["nivel"], antes, pendentes.get(origem)):
                causas = [f"{i['nome']} → {i['nivel']}" for i in modo["indicadores"] if i["nivel"] not in (None, "Normal")]
                msg = f"{modo['nome']}: {antes} → {modo['nivel']}. " + "; ".join(causas)
                gerados.append(self._alertar(instante, origem, modo["nivel"], antes, None, msg))

        antes = niveis_antes.get("global", "Normal")
        if self._deve_alertar(atual["nivel"], antes, pendentes.get("global")):
            msg = f"Nível global {antes} → {atual['nivel']}. " + "; ".join(atual["motivos"])
            gerados.append(self._alertar(instante, "global", atual["nivel"], antes, atual["indice"], msg))
        return gerados

    @staticmethod
    def _deve_alertar(nivel, anterior, pendente):
        if NIVEIS.index(nivel) <= NIVEIS.index(anterior):
            return False
        return pendente is None or NIVEIS.index(nivel) > NIVEIS.index(pendente)

    def _alertar(self, instante, origem, nivel, anterior, valor, mensagem):
        alerta_id = self.banco.inserir_alerta(instante, origem, nivel, anterior, valor, mensagem)
        log.warning("ALERTA [%s] %s", nivel, mensagem)
        return {"id": alerta_id, "origem": origem, "nivel": nivel, "mensagem": mensagem}

    def estado(self):
        avaliacao = self.banco.ultima_avaliacao()
        return {
            "avaliacao": avaliacao,
            "leituras": self.banco.ultimas_leituras(),
            "sensores": self.banco.sensores(),
            "alertas_pendentes": len(self.banco.alertas(apenas_pendentes=True, limite=1000)),
            "faixas_indice": config.FAIXAS_INDICE,
            "faixas_fs": config.FAIXAS_FS,
            "geotecnia": config.GEOTECNIA,
        }
