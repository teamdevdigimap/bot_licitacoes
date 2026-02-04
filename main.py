import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime
import bot_pncp
import bot_licita_ja
import bot_gemini 
import notifier
from sqlalchemy import create_engine, text

load_dotenv()

# print("enviando email teste")
# notifier.enviar_email('C:/Users/matheus.souza/OneDrive - Digimap/Área de Trabalho/Projetos/bot_licitacoes/bot_licitacoes/RELATORIO_NOVOS_20260101_20260615.csv', "mataugusto1999@gmail.com")

print("\n================ BOT LICITAÇÕES ================\n")
# ================= CONFIGURAÇÃO CENTRAL =================
#conexão do banco de dados
DB_CONNECTION = "postgresql://socio_user:s0C1o3@18.234.194.12/eletrobras_db_teste"

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


# ================= FUNÇÕES AUXILIARES =================
def ler_data_usuario(mensagem):
    entrada = input(mensagem).strip()
    if not entrada:
        return datetime.now().strftime("%Y%m%d")
    try:
        # Se digitar 01012024, converte para 20240101
        if len(entrada) == 8 and entrada.isdigit():
             dia, mes, ano = entrada[:2], entrada[2:4], entrada[4:]
             return f"{ano}{mes}{dia}"
        return entrada
    except:
        return datetime.now().strftime("%Y%m%d")

def tratar_valor_float(valor):
    if pd.isna(valor) or valor == "Não informado": return 0.0
    try:
        if isinstance(valor, (int, float)): return float(valor)
        limpo = str(valor).replace('.', '').replace(',', '.')
        return float(limpo)
    except: return 0.0

def limpar_formatacao_processo(valor):
    """Remove as aspas duplas/simples extras que usamos pro Excel"""
    if pd.isna(valor): return "Não informado"
    return str(valor).replace('"', '').replace("'", "").strip()

def processar_banco_de_dados(df_final):
    """
    Verifica duplicidade no banco, insere novos e retorna DF limpo (sem colunas de controle).
    """
    if df_final.empty:
        return df_final

    print("\n[BANCO] Conectando ao PostgreSQL...")
    
    try:
        engine = create_engine(DB_CONNECTION)
        
        # 1. Recupera chaves existentes
        print("[BANCO] Verificando registros existentes...")
        query_check = "SELECT num_processo, orgao_entidade FROM bot_licitacoes"
        
        try:
            df_banco = pd.read_sql(query_check, engine)
            df_banco['chave'] = df_banco['num_processo'].astype(str) + "_" + df_banco['orgao_entidade'].astype(str)
            set_existentes = set(df_banco['chave'])
        except Exception:
            set_existentes = set()

        # 2. Prepara o DataFrame Local
        df_insert = df_final.copy()
        df_insert['Num. Processo Limpo'] = df_insert['Num. Processo'].apply(limpar_formatacao_processo)
        df_insert['chave_temp'] = df_insert['Num. Processo Limpo'].astype(str) + "_" + df_insert['Órgão/Entidade'].astype(str)
        
        # 3. Filtra apenas NOVOS
        df_novos = df_insert[~df_insert['chave_temp'].isin(set_existentes)].copy()

        if df_novos.empty:
            print("[BANCO] Todas as licitações já estão cadastradas.")
            return pd.DataFrame() 

        print(f"[BANCO] Encontrados {len(df_novos)} NOVOS registros para inserir.")

        # 4. Ajusta colunas para SQL
        df_novos['valor_reais'] = df_novos['Valor (R$)'].apply(tratar_valor_float)
        df_novos['data_abertura'] = pd.to_datetime(df_novos['Data Abertura'], errors='coerce')
        df_novos['data_fechamento'] = pd.to_datetime(df_novos['Data Fechamento'], errors='coerce')
        df_novos['num_processo'] = df_novos['Num. Processo Limpo']

        # Mapeia colunas DF -> Banco
        mapa_db = {
            'Fonte API': 'fonte_api',
            'Local': 'local',
            'Órgão/Entidade': 'orgao_entidade',
            'Objeto da Licitação': 'obj_licitacao',
            'Link Sistema': 'link_sistema',
            'Modalidade': 'modalidade',
            'Modo Disputa': 'modo_disputa',
            'Usuário Responsável': 'responsavel',
            'IA_STATUS': 'status_ia',
            'IA_JUSTIFICATIVA': 'justificativa_ia'
        }
        df_renamed = df_novos.rename(columns=mapa_db)
        
        # Colunas calculadas
        df_renamed['sistema'] = df_renamed['fonte_api'] 
        df_renamed['data_insercao'] = datetime.now()

        # Seleciona colunas SQL
        colunas_tabela_sql = [
            "fonte_api", "local", "orgao_entidade", "num_processo", "obj_licitacao",
            "data_abertura", "data_fechamento", "valor_reais", "link_sistema",
            "sistema", "modalidade", "modo_disputa", "responsavel",
            "status_ia", "justificativa_ia", "data_insercao"
        ]
        
        # Garante colunas
        for col in colunas_tabela_sql:
            if col not in df_renamed.columns:
                df_renamed[col] = None

        df_to_sql = df_renamed[colunas_tabela_sql]

        # 5. Insere no Banco
        df_to_sql.to_sql('bot_licitacoes', engine, if_exists='append', index=False, chunksize=100)
        print("[BANCO] SUCESSO! Novos registros inseridos.")
        
        # =================================================================
        # LIMPEZA DO DATAFRAME DE RETORNO (Para o CSV ficar limpo)
        # =================================================================
        colunas_desejadas_csv = [
            'Fonte API', 'Local', 'Órgão/Entidade', 'Num. Processo', 
            'Objeto da Licitação', 'Data Abertura', 'Data Fechamento', 
            'Valor (R$)', 'Link Sistema', 'Modalidade', 'Modo Disputa', 
            'Usuário Responsável', 'IA_STATUS', 'IA_JUSTIFICATIVA'
        ]
        
        # Filtra apenas as colunas oficiais, ignorando as auxiliares de banco
        cols_finais = [c for c in colunas_desejadas_csv if c in df_novos.columns]
        return df_novos[cols_finais]

    except Exception as e:
        print(f"\n[ERRO CRÍTICO NO BANCO] {e}")
        # Em caso de erro, tenta limpar o DF original antes de devolver
        colunas_desejadas_csv = [
            'Fonte API', 'Local', 'Órgão/Entidade', 'Num. Processo', 
            'Objeto da Licitação', 'Data Abertura', 'Data Fechamento', 
            'Valor (R$)', 'Link Sistema', 'Modalidade', 'Modo Disputa', 
            'Usuário Responsável', 'IA_STATUS', 'IA_JUSTIFICATIVA'
        ]
        cols_exist = [c for c in colunas_desejadas_csv if c in df_final.columns]
        return df_final[cols_exist]

# ================= EXECUÇÃO =================

print("\n--- DEFINIÇÃO DO PERÍODO DE BUSCA ---")
print("Digite apenas números. Ex: 01022026 para 01/02/2026")
DATA_INICIO = ler_data_usuario("Data INICIAL (DDMMAAAA): ")
DATA_FIM    = ler_data_usuario("Data FINAL   (DDMMAAAA): ")

print("==================================================")
print(f"   COLETOR + IA + BANCO ({DATA_INICIO}-{DATA_FIM})")
print("==================================================")

# 1. Coleta
df_pncp = bot_pncp.executar_coleta_pncp(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)
df_licitaja = bot_licita_ja.executar_coleta_licitaja(DATA_INICIO, DATA_FIM, PALAVRAS_CHAVE)

if df_pncp is None: df_pncp = pd.DataFrame()
if df_licitaja is None: df_licitaja = pd.DataFrame()

# 2. Consolidação
print("\n--- Unificando Dados ---")
lista_dfs = []
if not df_pncp.empty: lista_dfs.append(df_pncp)
if not df_licitaja.empty: lista_dfs.append(df_licitaja)

if lista_dfs:
    df_final = pd.concat(lista_dfs, ignore_index=True)
    
    # Deduplicação Básica
    subset_cols = ['Link Sistema', 'Num. Processo', 'Órgão/Entidade']
    valid_cols = [c for c in subset_cols if c in df_final.columns]
    if valid_cols:
        df_final = df_final.drop_duplicates(subset=valid_cols)

    if 'Data Abertura' in df_final.columns:
        df_final = df_final.sort_values(by='Data Abertura', ascending=False)
    
    print(f"\n[SISTEMA] {len(df_final)} licitações encontradas (Bruto).")

    # 3. Análise IA (Gemini)
    if GEMINI_API_KEY:
        try:
            df_final = bot_gemini.processar_lote_gemini(df_final, GEMINI_API_KEY, PERFIL_EMPRESA)
            
            if 'IA_STATUS' in df_final.columns:
                qtd_antes = len(df_final)
                df_final = df_final[df_final['IA_STATUS'].str.upper() != "NÃO ATENDE"]
                print(f"[FILTRO IA] {qtd_antes - len(df_final)} descartados. Restam {len(df_final)}.")
        except Exception as e:
            print(f"[ERRO IA] {e}")
    else:
        print("[AVISO] Chave Gemini não encontrada. Pulando IA.")

    # 4. Banco de Dados e Exportação CSV
    if not df_final.empty:
        # Tenta inserir no banco e retorna DF LIMPO apenas com os novos
        df_novos = processar_banco_de_dados(df_final)

        if not df_novos.empty:
            print("\n--- Amostra de NOVOS Registros ---")
            pd.set_option('display.max_columns', None)
            # Mostra apenas colunas principais
            cols_show = ['IA_STATUS', 'Órgão/Entidade', 'Num. Processo']
            cols_ex = [c for c in cols_show if c in df_novos.columns]
            print(df_novos[cols_ex].head().to_string())

            nome_arquivo = f"RELATORIO_NOVOS_{DATA_INICIO}_{DATA_FIM}.csv"
            caminho = os.path.join(CAMINHO_ATUAL, nome_arquivo)
            
            df_novos.to_csv(caminho, index=False, sep=';', encoding='utf-8-sig')
            print(f"\n[SUCESSO] CSV salvo (sem colunas de controle): {caminho}\n")

            
            # --- NOVA PARTE DE ENVIO ---
            print("\n--- Iniciando Envios Automáticos ---\n")
            
            # Enviar por E-mail
            notifier.enviar_email(caminho, "Evelyn@sibbrasil.com")
            # notifier.enviar_email(caminho, "mataugusto1999@gmail.com")
            
            # Enviar por WhatsApp
            # notifier.enviar_whatsapp(caminho, "5521975531317")
            print("\n[FIM] Processamento concluído.")
        else:
            print("\n[FIM] Todos os registros já estavam no banco. Nenhum CSV gerado.")
    else:
        print("\n[FIM] Nenhuma licitação válida restante.")

else:
    print("\n[FIM] Nenhuma licitação encontrada.")

