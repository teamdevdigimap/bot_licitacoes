import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')

if not api_key:
    print("Erro: Chave não encontrada no .env")
else:
    genai.configure(api_key=api_key)
    print("--- Modelos Disponíveis para Geração de Conteúdo ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Nome: {m.name}")
    except Exception as e:
        print(f"Erro ao listar modelos: {e}")