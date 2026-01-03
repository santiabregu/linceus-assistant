# Módulo de integración con Gemini API
# Usado para interpretar consultas complejas y generar filtros estructurados

import os
import json
from typing import Optional, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configurar Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configurada correctamente")
else:
    print("WARNING: GEMINI_API_KEY no encontrada en .env")


# Schema de la base de datos para el prompt
SCHEMA_ASIGNATURAS = """
Tabla: asignaturas
Campos:
- codigo (TEXT): Código único de la asignatura, ej: "2050001"
- nombre (TEXT): Nombre completo, ej: "Fundamentos de Programación"
- curso (INTEGER): Año del grado (1, 2, 3, 4)
- creditos (DECIMAL): Créditos ECTS, ej: 6.0, 12.0
- duracion (TEXT): "A" = Anual, "C1" = Primer Cuatrimestre, "C2" = Segundo Cuatrimestre
- tipologia (TEXT): "Formacion_Basica", "Obligatoria", "Optativa"
- es_formacion_basica (BOOLEAN)
- es_optativa (BOOLEAN)
- activa (BOOLEAN): Si la asignatura está activa actualmente
"""


def interpretar_consulta_asignatura(pregunta: str) -> Optional[Dict[str, Any]]:
    """
    Usa Gemini para interpretar una consulta en lenguaje natural
    y devuelve filtros estructurados para la query.
    
    Returns:
        Dict con estructura:
        {
            "tipo": "especifica" | "filtrada" | "listado",
            "filtros": {
                "codigo": "2050001",  # opcional
                "nombre": "Redes",     # opcional
                "curso": 1,            # opcional
                "tipologia": "Obligatoria",  # opcional
                "duracion": "A",       # opcional
            },
            "atributo_solicitado": "creditos",  # opcional, si pide algo específico
            "limite": 10  # opcional, para listados
        }
    """
    if not GEMINI_API_KEY:
        return None
    
    prompt = f"""Eres un asistente que interpreta consultas sobre asignaturas universitarias.

{SCHEMA_ASIGNATURAS}

Dada la siguiente pregunta del usuario, genera un JSON con los filtros necesarios para buscar en la base de datos.

REGLAS:
1. Si menciona un código específico (ej: "2050001"), usa "codigo"
2. Si menciona un nombre o parte del nombre, usa "nombre" 
3. Si dice "primero", "primer curso", "1º", etc. → curso: 1
4. Si dice "obligatoria", "obligatorias" → tipologia: "Obligatoria"
5. Si dice "optativa", "optativas" → tipologia: "Optativa"
6. Si dice "formación básica", "básicas" → tipologia: "Formacion_Basica"
7. Si dice "anual", "anuales" → duracion: "A"
8. Si dice "primer cuatrimestre" → duracion: "C1"
9. Si dice "segundo cuatrimestre" → duracion: "C2"
10. Si pide un atributo específico (créditos, curso, etc.), indica en "atributo_solicitado"
11. Si es una lista general, pon "tipo": "listado"
12. Si busca una asignatura específica, pon "tipo": "especifica"
13. Si busca con filtros, pon "tipo": "filtrada"

PREGUNTA: "{pregunta}"

Responde SOLO con el JSON, sin explicaciones ni markdown:
"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Extraer JSON de la respuesta
        texto = response.text.strip()
        
        # Limpiar si viene con markdown
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        texto = texto.strip()
        
        resultado = json.loads(texto)
        return resultado
        
    except json.JSONDecodeError as e:
        print(f"Error parseando JSON de Gemini: {e}")
        print(f"Respuesta raw: {response.text}")
        return None
    except Exception as e:
        print(f"Error llamando a Gemini: {e}")
        return None


def generar_respuesta_natural(datos: list, pregunta_original: str) -> str:
    """
    Usa Gemini para generar una respuesta natural basada en los datos.
    """
    if not GEMINI_API_KEY or not datos:
        return None
    
    # Limitar datos para no exceder tokens
    datos_limitados = datos[:10]
    
    prompt = f"""Eres un asistente universitario amable. 
    
El usuario preguntó: "{pregunta_original}"

Los datos encontrados son:
{json.dumps(datos_limitados, ensure_ascii=False, indent=2)}

Genera una respuesta natural y concisa en español. 
- Si hay varios resultados, listarlos de forma clara
- Si hay muchos (más de 5), menciona cuántos hay y muestra los primeros
- Usa bullet points si es necesario
- No uses markdown, solo texto plano con saltos de línea

Respuesta:"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generando respuesta natural: {e}")
        return None
