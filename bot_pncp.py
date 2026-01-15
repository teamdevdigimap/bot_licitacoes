# Código das Modalidades de Licitação no PNCP:
# ● (código = 1) Leilão - Eletrônico
# ● (código = 2) Diálogo Competitivo
# ● (código = 3) Concurso
# ● (código = 4) Concorrência - Eletrônica
# ● (código = 5) Concorrência - Presencial
# ● (código = 6) Pregão - Eletrônico
# ● (código = 7) Pregão - Presencial
# ● (código = 8) Dispensa de Licitação
# ● (código = 9) Inexigibilidade
# ● (código = 10) Manifestação de Interesse
# ● (código = 11) Pré-qualificação
# ● (código = 12) Credenciamento
# ● (código = 13) Leilão - Presencial

import requests
import pandas as pd
import time
import re

def limpar_texto(texto):
    if pd.isna(texto): return ""
    texto = str(texto)
    texto_limpo = re.sub(r'[\r\n\t;]', ' ', texto)
    return " ".join(texto_limpo.split())

def formatar_processo(valor):
    if pd.isna(valor) or valor == "" or valor == "Não informado":
        return "Não informado"
    val_str = str(valor)
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    return f"'{val_str}"

def executar_coleta_pncp(data_inicio, data_fim, palavras_chave):
    print(f"\n[PNCP] Iniciando Coleta: {data_inicio} a {data_fim}")
    
    BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    #modalidade de pregão eletrônico
    MODALIDADES = [6, 7]

    todos_registros = []

    for cod_mod in MODALIDADES:
        print(f"[PNCP] > Consultando Modalidade: {cod_mod}...")
        pagina = 1
        max_paginas = 10

        while pagina <= max_paginas:
            params = {
                "dataInicial": data_inicio,
                "dataFinal": data_fim,
                "codigoModalidadeContratacao": cod_mod,
                "pagina": pagina,
                "tamanhoPagina": 50
            }

            try:
                response = requests.get(BASE_URL, params=params, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    itens = data.get('data', [])
                    if not itens: break
                    todos_registros.extend(itens)
                    if pagina >= data.get('totalPaginas', 1): break
                    pagina += 1
                    time.sleep(0.5)
                else:
                    break
            except Exception as e:
                print(f"  [PNCP] Erro: {e}")
                break

    if todos_registros:
        df = pd.DataFrame(todos_registros)

        if 'orgaoEntidade' in df.columns:
            df['Nome_Orgao'] = df['orgaoEntidade'].apply(
                lambda x: x.get('razaoSocial', str(x)) if isinstance(x, dict) else str(x)
            )

        def extrair_local(x):
            if isinstance(x, dict):
                muni = x.get('municipioNome', '')
                uf = x.get('ufSigla', '')
                if muni and uf: return f"{muni} - {uf}"
                return muni or uf
            return "Não informado"

        if 'unidadeOrgao' in df.columns:
            df['Local_Licitacao'] = df['unidadeOrgao'].apply(extrair_local)
        else:
            df['Local_Licitacao'] = "Não informado"

        if palavras_chave:
            regex = '|'.join(palavras_chave)
            mask = df['objetoCompra'].str.contains(regex, case=False, na=False)
            df_final = df[mask].copy()
        else:
            df_final = df.copy()

        if not df_final.empty:
            # --- LIMPEZA DE TEXTO (Evita mesclagem) ---
            cols_texto = ['Nome_Orgao', 'Local_Licitacao', 'objetoCompra']
            for col in cols_texto:
                if col in df_final.columns:
                    df_final[col] = df_final[col].apply(limpar_texto)

            # --- CORREÇÃO PROCESSO ---
            if 'processo' in df_final.columns:
                df_final['Num. Processo'] = df_final['processo'].apply(formatar_processo)
            else:
                df_final['Num. Processo'] = "Não informado"

            # Formatação Moeda
            df_final['valorTotalEstimado'] = pd.to_numeric(df_final['valorTotalEstimado'], errors='coerce').fillna(0.0)
            def formatar_brl(valor):
                if pd.isna(valor) or valor == 0: return "0,00"
                texto = f"{valor:,.2f}"
                return texto.replace(",", "X").replace(".", ",").replace("X", ".")
            df_final['Valor_R$'] = df_final['valorTotalEstimado'].apply(formatar_brl)
            
            df_final['Fonte API'] = 'PNCP'

            mapa_renomeacao = {
                'Local_Licitacao': 'Local',
                'Nome_Orgao': 'Órgão/Entidade',
                'objetoCompra': 'Objeto da Licitação',
                'dataAberturaProposta': 'Data Abertura',
                'dataEncerramentoProposta': 'Data Fechamento',
                'linkSistemaOrigem': 'Link Sistema',
                'modalidadeNome': 'Modalidade',
                'modoDisputaNome': 'Modo Disputa',
                'usuarioNome': 'Usuário Responsável'
            }
            
            df_exportacao = df_final.rename(columns=mapa_renomeacao)
            
            colunas_padrao = [
                'Fonte API', 'Local', 'Órgão/Entidade', 'Num. Processo', 
                'Objeto da Licitação', 'Data Abertura', 'Data Fechamento', 
                'Valor (R$)', 'Link Sistema', 'Modalidade', 'Modo Disputa', 
                'Usuário Responsável'
            ]
            
            cols_existentes = [c for c in colunas_padrao if c in df_exportacao.columns]
            print(f"[PNCP] {len(df_exportacao)} registros processados.")
            return df_exportacao[cols_existentes]

    print("[PNCP] Nenhum registro encontrado.")
    return pd.DataFrame()