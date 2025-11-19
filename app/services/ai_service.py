import os
from google import genai
from dotenv import load_dotenv
import dash_bootstrap_components as dbc
from dash import dcc

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash" 

client = None
gemini_configurado = False

if API_KEY:
    try:
        client = genai.Client()
        gemini_configurado = True
    except Exception as e:
        print(f"ERRO DE CONFIGURAÇÃO DE IA: {e}")

def generate_analysis_component(prompt):
    
    if not gemini_configurado:
        return dbc.Alert(
            "Erro de Configuração: API do Gemini não encontrada. Verifique o .env.", 
            color="danger", 
            className="mt-3"
        )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return dbc.Card(
            dbc.CardBody(dcc.Markdown(response.text)), 
            className="mt-3"
        )
    except Exception as e:
        return dbc.Alert(
            f"Erro na API do Gemini: {str(e)}", 
            color="danger", 
            className="mt-3"
        )