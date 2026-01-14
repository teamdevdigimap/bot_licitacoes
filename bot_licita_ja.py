import requests
import pandas as pd
import time
import re

def limpar_texto(texto):
    """Remove caracteres que quebram o CSV (Enter, Tab, Ponto-e-vírgula)"""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    # Substitui quebras de linha e ; por espaço
    texto_limpo = re.sub(r'[\r\n\t;]', ' ', texto)
    return " ".join(texto_limpo.split())

def formatar_processo(valor):
    """Força o Excel a ler como texto adicionando ' no início"""
    if pd.isna(valor) or valor == "" or valor == "Não informado":
        return "Não informado"
    
    val_str = str(valor)
    # Se for float (ex: 123.0), remove o decimal
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
        
    # Adiciona o apóstrofo para travar a formatação no Excel
    return f"'{val_str}"

def executar_coleta_licitaja(data_inicio_raw, data_fim_raw, palavras_chave):
    dt_ini_fmt = f"{data_inicio_raw[:4]}-{data_inicio_raw[4:6]}-{data_inicio_raw[6:]}"
    dt_fim_fmt = f"{data_fim_raw[:4]}-{data_fim_raw[4:6]}-{data_fim_raw[6:]}"

    print(f"\n[LicitaJá] Iniciando Coleta: {dt_ini_fmt} a {dt_fim_fmt}")
    
    API_KEY = "46BE17D544506A8DE5996A880613D6FA".strip()
    BASE_URL = "https://www.licitaja.com.br/api/v1/tender/search"
    MAX_PAGINAS = 3
    ITENS_POR_PAGINA = 50

    todos_registros = []
    headers = {
        "X-API-KEY": API_KEY,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }

    for i, termo in enumerate(palavras_chave):
        if i > 0 and i % 10 == 0:
            print(f"\n[LicitaJá] Pausa de segurança (90s) para API...")
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
                "smartsearch": 0 # Mantemos 0 para tentar ser estrito na API também
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

    # --- PROCESSAMENTO E FILTRAGEM RIGOROSA ---
    if todos_registros:
        df = pd.DataFrame(todos_registros)
        
        # Remove duplicatas brutas
        if 'id' in df.columns:
            df = df.drop_duplicates(subset=['id'])

        if not df.empty:
            # ==============================================================================
            # FILTRAGEM RIGOROSA LOCAL (PENTE FINO)
            # ==============================================================================
            print("[LicitaJá] Aplicando filtro rigoroso de palavras-chave nos objetos...")
            qtd_antes = len(df)
            
            # Cria regex com todas as palavras (ex: "geo|drone|map")
            # re.IGNORECASE faz ignorar maiúsculas/minúsculas
            regex_termos = '|'.join([re.escape(p) for p in palavras_chave])
            
            # Garante que tender_object seja string
            df['tender_object'] = df['tender_object'].astype(str)
            
            # Filtra: Mantém apenas se encontrar ALGUM termo no objeto da licitação
            mask = df['tender_object'].str.contains(regex_termos, case=False, regex=True)
            df = df[mask].copy()
            
            qtd_depois = len(df)
            print(f"[LicitaJá] Filtro aplicado: {qtd_antes} -> {qtd_depois} registros restantes.")
            # ==============================================================================

            if df.empty:
                print("[LicitaJá] Nenhum registro sobrou após o filtro rigoroso.")
                return pd.DataFrame()

            # --- PADRONIZAÇÃO E LIMPEZA ---
            df['Fonte API'] = 'LicitaJá'
            
            colunas_texto = ['agency', 'tender_object', 'city', 'state']
            for col in colunas_texto:
                if col in df.columns:
                    df[col] = df[col].apply(limpar_texto)

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
            df['Link Sistema'] = df.get('url2')
            df['Link Sistema'] = df['Link Sistema'].fillna(df.get('url', ''))
            df['Data Fechamento'] = df.get('opening_date_to', 'Não informado')
            df['Modo Disputa'] = "Não informado"

            mapa_colunas = {
                'agency': 'Órgão/Entidade',
                'tender_object': 'Objeto da Licitação',
                'publish_date': 'Data Abertura', 
                'type': 'Modalidade'
            }
            df = df.rename(columns=mapa_colunas)

            colunas_padrao = [
                'Fonte API', 'Local', 'Órgão/Entidade', 'Num. Processo', 
                'Objeto da Licitação', 'Data Abertura', 'Data Fechamento', 
                'Valor (R$)', 'Link Sistema', 'Modalidade', 'Modo Disputa', 
                'Usuário Responsável'
            ]
            
            cols_existentes = [c for c in colunas_padrao if c in df.columns]
            print(f"[LicitaJá] {len(df)} registros processados e exportados.")
            return df[cols_existentes]

    print("[LicitaJá] Nenhum registro encontrado.")
    return pd.DataFrame()