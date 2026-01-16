import google.generativeai as genai
import pandas as pd
import json
import os
import time
from dotenv import load_dotenv

# Carrega variáveis
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERRO CRÍTICO: Chave GEMINI_API_KEY não encontrada no .env")
else:
    genai.configure(api_key=api_key)

def processar_lote(model, lote):
    """
    Envia lote para API e garante retorno do mesmo tamanho da entrada.
    """
    # Prompt otimizado para resposta JSON estrita
    prompt_sistema = """
    Aja como especialista em licitações de Engenharia e Geotecnologia.
    Analise os objetos abaixo. Retorne um JSON (lista de objetos) contendo:
    - "id": (o mesmo ID recebido)
    - "IA_STATUS": "SIM" (se for pertinente a engenharia/geo), "NAO" ou "DUVIDA".
    - "IA_JUSTIFICATIVA": Max 10 palavras.
    
    IMPORTANTE: Responda APENAS o JSON válido. Sem crase, sem markdown.
    """
    
    texto_lote = ""
    ids_no_lote = []
    
    # Prepara os dados do lote
    for index, row in lote.iterrows():
        # Tenta pegar ID do PNCP, se não tiver pega do LicitaJa, se não tiver usa o Index
        id_lic = str(row.get('id_pncp', row.get('id_licitaja', index)))
        obj = str(row.get('objeto', 'Sem objeto')).replace('\n', ' ')
        
        texto_lote += f'{{ "id": "{id_lic}", "objeto": "{obj}" }}\n'
        ids_no_lote.append(id_lic)

    prompt_completo = f"{prompt_sistema}\n\nITENS PARA ANALISAR:\n{texto_lote}"

    # Tenta enviar para a IA
    try:
        response = model.generate_content(prompt_completo)
        
        # Limpeza bruta do texto para evitar erros de formatação da IA
        texto_limpo = response.text.strip()
        if texto_limpo.startswith("```json"):
            texto_limpo = texto_limpo.replace("```json", "").replace("```", "")
        elif texto_limpo.startswith("```"):
            texto_limpo = texto_limpo.replace("```", "")
            
        json_retorno = json.loads(texto_limpo)
        return json_retorno

    except Exception as e:
        print(f"   [ERRO LOTE] Falha na API: {e}")
        # CRUCIAL: Retorna lista de erros do mesmo tamanho do lote para não desalinas a planilha
        lista_erro = []
        for id_falha in ids_no_lote:
            lista_erro.append({
                "id": id_falha,
                "IA_STATUS": "ERRO API",
                "IA_JUSTIFICATIVA": "Falha na conexão ou JSON inválido"
            })
        return lista_erro

def analisar_licitacoes_com_gemini(df):
    if df.empty:
        return df

    # Usa modelo estável PRO (evita o erro 404 do Flash)
    NOME_MODELO = 'gemini-pro'
    print(f"\n[GEMINI] Iniciando análise de {len(df)} registros usando {NOME_MODELO}...")
    
    try:
        model = genai.GenerativeModel(NOME_MODELO)
    except Exception as e:
        print(f"Erro ao instanciar modelo: {e}")
        return df

    resultados_ia = []
    TAMANHO_LOTE = 5  # Lotes pequenos evitam timeout
    
    total = len(df)
    
    for i in range(0, total, TAMANHO_LOTE):
        fim = min(i + TAMANHO_LOTE, total)
        lote = df.iloc[i:fim]
        
        print(f" > Processando {i+1} a {fim} de {total}...")
        
        res_lote = processar_lote(model, lote)
        resultados_ia.extend(res_lote)
        
        # Pausa para respeitar limite de requisições por minuto
        time.sleep(1.5)

    # --- Sincronização Final ---
    # Adiciona colunas ao DF original garantindo a ordem
    col_status = []
    col_justificativa = []
    
    # Se a IA devolveu menos registros que o DF, preenche com erro (Segurança)
    if len(resultados_ia) < total:
        print("[AVISO] IA retornou menos itens que o enviado. Preenchendo lacunas.")
        while len(resultados_ia) < total:
            resultados_ia.append({"IA_STATUS": "NAO PROCESSADO", "IA_JUSTIFICATIVA": "Erro contagem"})

    for res in resultados_ia:
        col_status.append(res.get('IA_STATUS', 'ERRO'))
        col_justificativa.append(res.get('IA_JUSTIFICATIVA', 'Sem resposta'))

    df_final = df.copy()
    df_final['IA_STATUS'] = col_status
    df_final['IA_JUSTIFICATIVA'] = col_justificativa
    
    return df_final