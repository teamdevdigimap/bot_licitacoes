import google.generativeai as genai
import pandas as pd
import json
import time
import math

def configurar_gemini(api_key):
    genai.configure(api_key=api_key)

def processar_lote_gemini(df, api_key, perfil_empresa):
    if df.empty:
        return df

    print(f"\n[GEMINI] Iniciando análise em LOTE de {len(df)} registros...")
    configurar_gemini(api_key)
    
    # Modelo Flash é ideal para grandes volumes de texto rápido
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Criamos uma cópia com ID temporário para garantir que a IA não se perca
    df_temp = df.copy().reset_index(drop=True)
    df_temp['ID_TEMP'] = df_temp.index
    
    # Colunas essenciais para a IA analisar (economiza tokens não enviando tudo)
    cols_analise = ['ID_TEMP', 'Órgão/Entidade', 'Objeto da Licitação']
    
    # Se o DF for maior que 30 linhas, dividimos em "chunks" para não estourar 
    # o limite de resposta (output tokens) do modelo.
    TAMANHO_CHUNK = 30
    total_chunks = math.ceil(len(df_temp) / TAMANHO_CHUNK)
    
    todos_resultados = []

    for i in range(total_chunks):
        inicio = i * TAMANHO_CHUNK
        fim = inicio + TAMANHO_CHUNK
        chunk = df_temp.iloc[inicio:fim]
        
        print(f"  > Processando lote {i+1}/{total_chunks} ({len(chunk)} itens)...")
        
        # Converte o pedaço da tabela para JSON string
        dados_json = chunk[cols_analise].to_json(orient='records', force_ascii=False)
        
        prompt = f"""
        Você é um analista sênior de licitações.
        
        PERFIL DA MINHA EMPRESA:
        {perfil_empresa}

        SUA TAREFA:
        Analise a lista de licitações abaixo (fornecida em JSON) e classifique a afinidade de cada uma com o meu perfil.

        CLASSIFICAÇÕES POSSÍVEIS:
        - "ATENDE": O objeto é compatível com meus serviços.
        - "ATENDE PARCIALMENTE": É da minha área, mas parece exigir complementos ou consórcio.
        - "NÃO ATENDE": Fora do meu escopo.

        DADOS DE ENTRADA:
        {dados_json}

        FORMATO DE SAÍDA (Obrigatório):
        Retorne APENAS um JSON válido (lista de objetos), sem markdown, contendo:
        - "ID_TEMP": O mesmo ID numérico da entrada.
        - "IA_STATUS": A classificação.
        - "IA_JUSTIFICATIVA": Explicação curta (máx 10 palavras).
        """

        try:
            response = model.generate_content(prompt)
            texto_resposta = response.text.strip()
            
            # Limpeza caso o Gemini mande ```json ... ```
            if texto_resposta.startswith("```"):
                texto_resposta = texto_resposta.replace("```json", "").replace("```", "").strip()
            
            resultados_json = json.loads(texto_resposta)
            todos_resultados.extend(resultados_json)
            
            # Pausa de segurança entre lotes
            time.sleep(2)
            
        except Exception as e:
            print(f"  [ERRO] Falha no lote {i+1}: {e}")
            # Em caso de erro, preenche dummy para não quebrar
            for idx in chunk['ID_TEMP']:
                todos_resultados.append({
                    "ID_TEMP": idx, 
                    "IA_STATUS": "ERRO API", 
                    "IA_JUSTIFICATIVA": str(e)
                })

    # --- MESCLAGEM DOS RESULTADOS ---
    print("[GEMINI] Consolidando análises...")
    
    df_resultados = pd.DataFrame(todos_resultados)
    
    # Garante que ID_TEMP seja int para o merge funcionar
    if not df_resultados.empty and 'ID_TEMP' in df_resultados.columns:
        df_resultados['ID_TEMP'] = df_resultados['ID_TEMP'].astype(int)
        
        # Junta os dados originais com a resposta da IA
        df_final = df_temp.merge(df_resultados, on='ID_TEMP', how='left')
        
        # Remove a coluna auxiliar
        df_final = df_final.drop(columns=['ID_TEMP'])
        
        return df_final
    else:
        print("[GEMINI] Não foi possível estruturar a resposta da IA.")
        return df