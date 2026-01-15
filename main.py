import pandas as pd
import os
from datetime import datetime
import bot_pncp
import bot_licita_ja

# ================= CONFIGURAÇÃO CENTRAL =================

# 1. Defina o período aqui
print("\n--- DEFINIÇÃO DO PERÍODO DE BUSCA ---\n")
print("insira a data no formato AnoMêsDia, em numeral. ex.: 20260115 -> 15 Jan 2026")
DATA_INICIO = input("\nDigite a Data INICIAL (AAAAMMDD): ").strip() or datetime.now().strftime("%Y%m%d")
DATA_FIM    = input("\nDigite a Data FINAL   (AAAAMMDD): ").strip() or datetime.now().strftime("%Y%m%d")

# 2. Lista de Palavras-Chave Expandida
PALAVRAS_CHAVE = [
    # Termos Originais
    "geoprocessamento", "mapeamento", "satélite", "topografia", "drone", 
    "batimetria", "georreferenciamento", "cartografia", "geografia", 
    "geoserviços", "sensoriamento remoto", "gisweb",
    "aerolevantamento", "sondagem", "sondagens", 
    "topográfico", "planialtimetria", "aeronave remotamente pilotada",
    
    # Novos Termos Correlatos
    "aerofotogrametria", "lidar", "radar", "gnss", 
    "regularização fundiária", "agrimensura",
    "cartográfica", "fotogrametria", 
    "imageamento", "ortofoto", 
    "levantamento aéreo", "levantamento topográfico", "mapeamento digital", 
    "geodésia", "geoinformação", "geotecnologia", "geoprocessamento ambiental",
    "geoprocessamento urbano", "geoprocessamento rural", "planialtimétrico",
    "georreferenciamento cartográfico", "sensoriamento remoto ambiental",
    "georreferenciado", "geotécnico", "sondagem de solo"
]

CAMINHO_ATUAL = os.getcwd()

# ================= EXECUÇÃO =================
print("==================================================")
print(f"   COLETOR UNIFICADO ({DATA_INICIO}-{DATA_FIM})")
print(f"   Termos a pesquisar: {len(PALAVRAS_CHAVE)}")
print("==================================================")

df_pncp = bot_pncp.executar_coleta_pncp(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)
df_licitaja = bot_licita_ja.executar_coleta_licitaja(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)

# ================= CONSOLIDAÇÃO =================
print("\n--- Processando Consolidação Final ---")

lista_dfs = []
if not df_pncp.empty: lista_dfs.append(df_pncp)
if not df_licitaja.empty: lista_dfs.append(df_licitaja)

if lista_dfs:
    df_final = pd.concat(lista_dfs, ignore_index=True)
    
    # ---------------------------------------------------------
    # REMOÇÃO DE DUPLICATAS FINAL
    # ---------------------------------------------------------
    qtd_antes = len(df_final)
    
    # Remove linhas onde Link, Órgão, Processo e Objeto sejam idênticos
    # (Isso resolve casos onde a mesma licitação aparece em palavras-chave diferentes)
    df_final = df_final.drop_duplicates(subset=['Link Sistema', 'Num. Processo', 'Órgão/Entidade'])
    
    qtd_depois = len(df_final)
    print(f"\n[SISTEMA] Deduplicação Final: {qtd_antes} -> {qtd_depois} registros únicos.")

    if 'Data Abertura' in df_final.columns:
        df_final = df_final.sort_values(by='Data Abertura', ascending=False)

    print("\n--- Amostra ---")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    cols_view = ['Fonte API', 'Órgão/Entidade', 'Num. Processo', 'Valor (R$)']
    existentes = [c for c in cols_view if c in df_final.columns]
    print(df_final[existentes].head().to_string())

    nome_arquivo = f"RELATORIO_FINAL_{DATA_INICIO}_{DATA_FIM}.csv"
    caminho = os.path.join(CAMINHO_ATUAL, nome_arquivo)
    
    df_final.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n[SUCESSO] Salvo em: {caminho}")
else:
    print("\n[AVISO] Nada encontrado.")