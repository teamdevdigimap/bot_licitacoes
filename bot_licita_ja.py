import requests
import pandas as pd
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Tenta pegar do .env, se não tiver, usa a fixa (fallback)
api_key_env = os.environ.get("LICITAJA_API_KEY")
API_KEY_FIXA = "46BE17D544506A8DE5996A880613D6FA" # Insira sua chave aqui se não usar .env

def limpar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto)
    texto_limpo = re.sub(r'[\r\n\t;]', ' ', texto)
    return " ".join(texto_limpo.split())

def formatar_processo(valor):
    """Envolve o valor em aspas duplas"""
    if pd.isna(valor) or valor == "" or valor == "Não informado":
        return "Não informado"
    
    val_str = str(valor)
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
        
    # ATUALIZADO: Coloca entre aspas duplas
    return f'"{val_str}"'

def executar_coleta_licitaja(data_inicio_raw, data_fim_raw, palavras_chave):
    dt_ini_fmt = f"{data_inicio_raw[:4]}-{data_inicio_raw[4:6]}-{data_inicio_raw[6:]}"
    dt_fim_fmt = f"{data_fim_raw[:4]}-{data_fim_raw[4:6]}-{data_fim_raw[6:]}"

    print(f"\n[LicitaJá] Iniciando Coleta: {dt_ini_fmt} a {dt_fim_fmt}")
    
    chave_final = api_key_env if api_key_env else API_KEY_FIXA
    
    BASE_URL = "https://www.licitaja.com.br/api/v1/tender/search"
    MAX_PAGINAS = 3
    ITENS_POR_PAGINA = 50

    todos_registros = []
    headers = {
        "X-API-KEY": chave_final.strip(),
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }

    for i, termo in enumerate(palavras_chave):
        # Pausa de segurança
        if i > 0 and i % 10 == 0:
            print(f"\n[LicitaJá] Pausa de segurança (90s)...")
            time.sleep(90)

        print(f"[LicitaJá] > Buscando termo ({i+1}/{len(palavras_chave)}): '{termo}'...")
        pagina = 1
        
        while pagina <= MAX_PAGINAS:
            params = {
                "keyword": termo,
                "publish_date_start": dt_ini_fmt,
                "publish_date_end": dt_fim_fmt,
                "agencyfilter": 0,
                "items": ITENS_POR_PAGINA,
                "page": pagina, 
                "smartsearch": 0 
            }

            try:
                response = requests.get(BASE_URL, headers=headers, params=params, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    itens = data.get('results', [])
                    if not itens: break
                    
                    todos_registros.extend(itens)
                    
                    if pagina >= data.get('total_pages', 1): break
                    pagina += 1
                    time.sleep(1)
                else:
                    break
            except Exception as e:
                print(f"  [LicitaJá] Erro: {e}")
                break

    if todos_registros:
        df = pd.DataFrame(todos_registros)
        
        # 1. DEDUPLICAÇÃO INTERNA (Pelo ID da API)
        if 'id' in df.columns:
            qtd_antes = len(df)
            df = df.drop_duplicates(subset=['id'])
            print(f"[LicitaJá] Deduplicação interna: {qtd_antes} -> {len(df)}")

        if not df.empty:
            # 2. FILTRO RIGOROSO PALAVRAS
            regex_termos = '|'.join([re.escape(p) for p in palavras_chave])
            df['tender_object'] = df['tender_object'].astype(str)
            mask_kw = df['tender_object'].str.contains(regex_termos, case=False, regex=True)
            df = df[mask_kw].copy()
            
            if df.empty: return pd.DataFrame()

            # 3. FILTRO MODALIDADE
            MODALIDADES_ALVO = ["PREGÃO ELETRÔNICO", "PREGÃO PRESENCIAL"]
            if 'type' in df.columns:
                mask_mod = df['type'].str.upper().isin(MODALIDADES_ALVO)
                df = df[mask_mod].copy()
            
            if df.empty: return pd.DataFrame()

            # Padronização
            df['Fonte API'] = 'LicitaJá'
            colunas_texto = ['agency', 'tender_object', 'city', 'state']
            for col in colunas_texto:
                if col in df.columns: df[col] = df[col].apply(limpar_texto)

            df['Local'] = df.apply(lambda x: f"{x.get('city', '')} - {x.get('state', '')}", axis=1)
            
            if 'value' in df.columns:
                df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0.0)
                def formatar_brl(valor):
                    if pd.isna(valor) or valor == 0: return "0,00"
                    texto = f"{valor:,.2f}"
                    return texto.replace(",", "X").replace(".", ",").replace("X", ".")
                df['Valor (R$)'] = df['value'].apply(formatar_brl)
            else:
                df['Valor (R$)'] = "0,00"

            df['temp_process'] = df.get('process', 'Não informado')
            df['Num. Processo'] = df['temp_process'].apply(formatar_processo)

            df['Usuário Responsável'] = df.get('biddingPlatform', 'Não informado')
            df['Link Sistema'] = df.get('url2').fillna(df.get('url', ''))
            
            if 'close_date' in df.columns and not df['close_date'].isna().all():
                 df['Data Fechamento'] = df['close_date']
            else:
                 df['Data Fechamento'] = df.get('opening_date_to', 'Não informado')

            df['Modo Disputa'] = "Não informado"

            mapa_colunas = {
                'agency': 'Órgão/Entidade',
                'tender_object': 'Objeto da Licitação',
                'type': 'Modalidade'
            }
            if 'publish_date' in df.columns: mapa_colunas['publish_date'] = 'Data Abertura'
            elif 'catalog_date' in df.columns: mapa_colunas['catalog_date'] = 'Data Abertura'
            
            df = df.rename(columns=mapa_colunas)

            colunas_padrao = [
                'Fonte API', 'Local', 'Órgão/Entidade', 'Num. Processo', 
                'Objeto da Licitação', 'Data Abertura', 'Data Fechamento', 
                'Valor (R$)', 'Link Sistema', 'Modalidade', 'Modo Disputa', 
                'Usuário Responsável'
            ]
            cols = [c for c in colunas_padrao if c in df.columns]
            print(f"[LicitaJá] {len(df)} registros processados.")
            return df[cols]

    return pd.DataFrame()