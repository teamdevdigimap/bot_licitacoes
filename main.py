import pandas as pd
import os
from datetime import datetime
import bot_pncp
import bot_licita_ja

# ================= CONFIGURAÇÃO CENTRAL =================

# 1. Defina o período aqui (Formato: AAAAMMDD)

print("\n--- DEFINIÇÃO DO PERÍODO DE BUSCA ---\n")
print("insira a data no formato AnoMêsDia, em numeral. ex.: 20260115 -> 15 Jan 2026")
DATA_INICIO = input("\nDigite a Data INICIAL (AAAAMMDD): ").strip() or datetime.now().strftime("%Y%m%d")
DATA_FIM    = input("\nDigite a Data FINAL   (AAAAMMDD): ").strip() or datetime.now().strftime("%Y%m%d")

# 2. Defina suas palavras-chave aqui
PALAVRAS_CHAVE = [
    "geoprocessamento", "mapeamento", "satélite", "topografia", "drone", 
    "batimetria", "georreferenciamento", "cartografia", "geografia", 
    "geoserviços", "sensoriamento remoto", "levantamento", 
    "aerolevantamento", "sondagem", "sondagens", "geotec", "geotéc", 
    "levantamento", "topográfico", "planialtim", "aeronave remotamente pilotada"
]
print(f"\nPalavras-chave definidas: {PALAVRAS_CHAVE}\n\n")

# 3. Local de Salvamento
CAMINHO_ATUAL = os.getcwd()

# ================= EXECUÇÃO =================
print("==================================================")
print(f"   COLETOR UNIFICADO - ({DATA_INICIO}-{DATA_FIM})")
print("==================================================")

df_pncp = bot_pncp.executar_coleta_pncp(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)
df_licitaja = bot_licita_ja.executar_coleta_licitaja(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)

# ================= CONSOLIDAÇÃO =================
print("\n--- Gerando Relatório Final ---")

lista_dfs = []
if not df_pncp.empty: lista_dfs.append(df_pncp)
if not df_licitaja.empty: lista_dfs.append(df_licitaja)

if lista_dfs:
    df_final = pd.concat(lista_dfs, ignore_index=True)
    if 'Data Abertura' in df_final.columns:
        df_final = df_final.sort_values(by='Data Abertura', ascending=False)

    print("\n--- Amostra ---")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    cols_view = ['Fonte API', 'Órgão/Entidade', 'Num. Processo', 'Valor (R$)']
    existentes = [c for c in cols_view if c in df_final.columns]
    print(df_final[existentes].head().to_string())

    nome_arquivo = f"RELATORIO_FINAL_LICITACOES_{DATA_INICIO}_{DATA_FIM}.csv"
    caminho = os.path.join(CAMINHO_ATUAL, nome_arquivo)
    
    # Salva com encoding 'utf-8-sig' para acentos no Excel e sep=';'
    df_final.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n[SUCESSO] Salvo em: {caminho}")
else:
    print("\n[AVISO] Nada encontrado.")
