import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash" 
client = None
gemini_configurado = False

if not API_KEY:
    print("ERRO DE CONFIGURAÇÃO DE IA: A variável de ambiente GEMINI_API_KEY não foi encontrada.")
else:
    try:
        client = genai.Client()
        gemini_configurado = True
        print("Serviço de IA (Gemini) configurado com sucesso.")
    except Exception as e:
        print(f"ERRO DE CONFIGURAÇÃO DE IA: {e}")