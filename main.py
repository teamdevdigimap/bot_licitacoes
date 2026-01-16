import pandas as pd
import os
from datetime import datetime
import bot_pncp
import bot_licita_ja
import bot_gemini 

# ================= CONFIGURAÇÃO CENTRAL =================

# 1. CHAVE GEMINI
# Obtenha em: https://aistudio.google.com/app/apikey
GEMINI_API_KEY = os.environ['GEMINI_API_KEY'] 

# 2. DEFINA SEU PERFIL
PERFIL_EMPRESA = """
Minha empresa atua com Engenharia e Geotecnologia.
Prestamos serviços de: Levantamento topográfico, aerofotogrametria com drones, 
batimetria, sondagens, georreferenciamento, cartografia, sensoriamento remoto, 
cadastro técnico e regularização fundiária (REURB).
NÃO fazemos: Obras civis pesadas (construção de prédios), pavimentação, limpeza ou vigilância.
"""

print("\n--- DEFINIÇÃO DO PERÍODO DE BUSCA ---\n")
DATA_INICIO = input("Digite a Data INICIAL (AAAAMMDD): ").strip() or datetime.now().strftime("%Y%m%d")
DATA_FIM    = input("Digite a Data FINAL   (AAAAMMDD): ").strip() or datetime.now().strftime("%Y%m%d")

PALAVRAS_CHAVE = [
    "geoprocessamento", "mapeamento", "satélite", "topografia", "drone", 
    "batimetria", "georreferenciamento", "cartografia", "geografia", 
    "geoserviços", "sensoriamento remoto", "gisweb",
    "aerolevantamento", "sondagem", "sondagens", 
    "topográfico", "planialtimetria", "aeronave remotamente pilotada",
    "aerofotogrametria", "lidar", "radar", "gnss", 
    "regularização fundiária", "agrimensura",
    "cartográfica", "fotogrametria", "agrimensor"
    "imageamento", "ortofoto", "levantamento topografico"
    "levantamento aéreo", "levantamento topográfico", "mapeamento digital", 
    "geodésia", "geoinformação", "geotecnologia", "geoprocessamento ambiental",
    "geoprocessamento urbano", "geoprocessamento rural", "planialtimétrico",
    "georreferenciamento cartográfico", "sensoriamento remoto ambiental",
    "georreferenciado", "geotécnico", "sondagem de solo"
]

print(f"\n--- Palavras-chave ({len(PALAVRAS_CHAVE)}) ---")

CAMINHO_ATUAL = os.getcwd()

# ================= EXECUÇÃO DA COLETA =================
print("\n==================================================")
print(f"   COLETOR UNIFICADO + IA GEMINI ({DATA_INICIO}-{DATA_FIM})")
print("==================================================")

df_pncp = bot_pncp.executar_coleta_pncp(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)
df_licitaja = bot_licita_ja.executar_coleta_licitaja(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)

# ================= CONSOLIDAÇÃO =================
print("\n--- Unificando Dados ---")

lista_dfs = []
if not df_pncp.empty: lista_dfs.append(df_pncp)
if not df_licitaja.empty: lista_dfs.append(df_licitaja)

if lista_dfs:
    df_final = pd.concat(lista_dfs, ignore_index=True)
    
    # Deduplicação Final
    subset_cols = ['Link Sistema', 'Num. Processo', 'Órgão/Entidade']
    valid_cols = [c for c in subset_cols if c in df_final.columns]
    if valid_cols:
        df_final = df_final.drop_duplicates(subset=valid_cols)
    
    if 'Data Abertura' in df_final.columns:
        df_final = df_final.sort_values(by='Data Abertura', ascending=False)

    print(f"\n[SISTEMA] {len(df_final)} licitações encontradas antes da IA.")

    # ================= ANÁLISE COM GEMINI (LOTE) =================
    if GEMINI_API_KEY and "COLE_SUA_CHAVE" not in GEMINI_API_KEY:
        try:
            df_final = bot_gemini.processar_lote_gemini(
                df_final, 
                GEMINI_API_KEY, 
                PERFIL_EMPRESA
            )
            
            # --- FILTRAGEM PÓS-IA (NOVO BLOCO) ---
            if 'IA_STATUS' in df_final.columns:
                print("\n[FILTRO FINAL] Removendo itens classificados como 'NÃO ATENDE'...")
                qtd_antes = len(df_final)
                
                # Mantém apenas o que for diferente de "NÃO ATENDE"
                # (Mantém "ATENDE", "ATENDE PARCIALMENTE" e erros para análise manual)
                df_final = df_final[df_final['IA_STATUS'].str.upper() != "NÃO ATENDE"]
                
                qtd_depois = len(df_final)
                removidos = qtd_antes - qtd_depois
                print(f"[FILTRO FINAL] {removidos} licitações descartadas. Restaram {qtd_depois}.")
            # -------------------------------------
            
        except Exception as e:
            print(f"[ERRO GERAL IA] {e}")
    else:
        print("\n[AVISO] IA ignorada (Chave não configurada no script).")

    # ================= SALVAMENTO =================
    if not df_final.empty:
        print("\n--- Amostra Final (Filtrada) ---")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        cols_view = ['IA_STATUS', 'IA_JUSTIFICATIVA', 'Órgão/Entidade', 'Objeto da Licitação']
        cols_exist = [c for c in cols_view if c in df_final.columns]
        print(df_final[cols_exist].head().to_string())

        nome_arquivo = f"RELATORIO_IA_{DATA_INICIO}_{DATA_FIM}.csv"
        caminho = os.path.join(CAMINHO_ATUAL, nome_arquivo)
        
        df_final.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n[SUCESSO] Relatório salvo em: {caminho}")
    else:
        print("\n[AVISO] Todas as licitações foram filtradas ou nenhuma foi encontrada.")

else:
    print("\n[AVISO] Nenhuma licitação encontrada.")