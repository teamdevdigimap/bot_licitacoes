# 🤖 Bot de Licitações - Digimap

> **Versão 2026**

Este projeto é uma ferramenta de automação desenvolvida para monitorar, coletar e analisar oportunidades de licitações públicas. O bot integra dados das APIs **Licita Já** e **PNCP** (Portal Nacional de Contratações Públicas) e utiliza a Inteligência Artificial do **Google Gemini** para filtrar e qualificar as oportunidades de acordo com o perfil da empresa.

---

## 🚀 Funcionalidades

* **Coleta Unificada:** Busca editais em múltiplas fontes (PNCP e Licita Já).
* **Filtragem por Palavras-Chave:** Seleciona apenas licitações relevantes para o setor (Engenharia, Geotecnologia, etc.).
* **Análise com IA:** Utiliza o Google Gemini para ler os objetos das licitações e justificar a pertinência (Sim/Não).
* **Exportação:** Gera relatórios detalhados em CSV/Excel.

---

## 🛠️ Tecnologias Utilizadas

* [Python 3.x](https://www.python.org/)
* [Pandas](https://pandas.pydata.org/) (Manipulação de dados)
* **APIs:** PNCP & Licita Já
* **IA:** Google Gemini (Generative AI)

---

## ⚙️ Configuração e Instalação

Siga os passos abaixo para executar o projeto em um ambiente virtual local.

### 1. Clonar ou baixar o repositório

Certifique-se de ter os arquivos do projeto no seu computador.

### 2. Criar o Ambiente Virtual

Abra o terminal na pasta do projeto e execute:

```bash
python -m venv venv

```

*Isso criará uma pasta chamada `venv` isolada para as dependências.*

### 3. Ativar o Ambiente Virtual

* **No Windows:**
```bash
venv\Scripts\Activate

```


> ⚠️ **Nota:** Se receber um erro de *Execution_Policies* no PowerShell, execute o comando abaixo e tente ativar novamente:


> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> 
> ```
> 
> 


* **No Linux/Mac:**
```bash
source venv/bin/activate

```



### 4. Instalar Dependências

Com o ambiente ativo (o terminal mostrará `(venv)` no início), instale as bibliotecas necessárias:

```bash
pip install -r requirements.txt

```

---

## 🔑 Configuração das Chaves de API

Para que o bot funcione, você precisa configurar as variáveis de ambiente.

1. Renomeie o arquivo `.env.example` para `.env`.
2. Insira suas chaves nos campos correspondentes dentro do arquivo `.env`.

**Onde conseguir as chaves:**

* **Licita Já:** [Gerar Chave de Acesso de Integração](https://www.google.com/search?q=https://www.licitaja.com.br/api_integration.php%3F)
* **Google Gemini:** [Gerar API Key no AI Studio](https://aistudio.google.com/app/api-keys)

**Exemplo do arquivo `.env`:**

```env
GEMINI_API_KEY="sua_chave_do_google_aqui"
LICITAJA_API_KEY="seu_token_licita_ja_aqui"

```

---

## ▶️ Como Executar

Com o ambiente ativado e as chaves configuradas, inicie o bot:

```bash
python main.py

```

Siga as instruções no terminal para definir o período de busca (Data Inicial e Final). O relatório será salvo na pasta raiz do projeto ao final da execução.

---

## ⚠️ Solução de Problemas (Erro de API)

Caso você encontre erros relacionados à IA, como:

> `404 models/gemini-1.5-flash is not found`

Isso significa que a biblioteca está desatualizada ou sua chave não tem acesso ao modelo configurado. Siga os passos:

1. Atualize a biblioteca do Google:
```bash
pip install -U google-generativeai

```


2. Execute o script de diagnóstico incluído no projeto para ver quais modelos estão disponíveis para você:
```bash
python teste_modelos.py

```


*Se este arquivo não existir, crie-o com o seguinte conteúdo:*
```python
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

print("--- Modelos Disponíveis ---")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Nome: {m.name}")

```


3. Verifique o nome do modelo que aparecer no terminal (ex: `gemini-pro` ou `gemini-1.5-flash`) e atualize a linha correspondente no arquivo `bot_gemini.py`.

---

## 📝 Licença

Desenvolvido por **Digimap** - 2026.