"""
Script de prueba para depurar generación de SQL.
Ejecutar: python test_text_to_sql.py
"""

import time
from actions.text_to_sql import generar_sql_listado, generar_sql_especifica, ejecutar_query
from actions.gemini_client import verificar_gemini_activo
from actions.config import BotConfig
from actions.db import db_client

def obtener_titulacion_id():
    """Obtiene el UUID de la titulación por defecto desde la BD."""
    codigo_titulacion = BotConfig.get_default_titulacion()
    
    query = "SELECT id FROM titulaciones WHERE codigo = %s AND activa = true LIMIT 1"
    exito, resultado = ejecutar_query(query, [codigo_titulacion])
    
    if exito and resultado:
        titulacion_id = resultado[0].get('id')
        print(f"✅ Titulación encontrada: {codigo_titulacion} → {titulacion_id}")
        return str(titulacion_id)
    else:
        print(f"⚠️  No se encontró titulación con código {codigo_titulacion}")
        return None

def test_sql_listado(contexto_titulacion=None):
    """Prueba generación de SQL para listados."""
    print("="*60)
    print("TEST: Generación SQL - Listado")
    print(f"Contexto: Titulación ID = {contexto_titulacion}")
    print("="*60)
    
    preguntas = [
        "dame las asignaturas del primero",
        "asignaturas optativas de cuarto",
        "obligatorias de segundo",
        "asignaturas anuales de tercero",
    ]
    
    for pregunta in preguntas:
        print(f"\n📝 Pregunta: '{pregunta}'")
        print("-" * 60)
        
        # Medir tiempo de generación SQL
        inicio_sql = time.time()
        resultado = generar_sql_listado(pregunta, contexto_titulacion=contexto_titulacion)
        tiempo_sql = time.time() - inicio_sql
        
        print(f"⏱️  Tiempo generación SQL: {tiempo_sql:.2f}s")
        print(f"✅ SQL generada:")
        print(f"   {resultado.get('sql', 'N/A')}")
        print(f"📊 Filtros detectados: {resultado.get('filtros_aplicados', {})}")
        print(f"💡 Explicación: {resultado.get('explicacion', 'N/A')}")
        print(f"🔍 Es fallback: {'Sí' if resultado.get('explicacion') == 'fallback - lista todas las asignaturas' else 'No'}")
        
        # Probar ejecutar la query y medir tiempo
        if resultado.get('valido'):
            inicio_query = time.time()
            exito, resultados = ejecutar_query(
                resultado['sql'],
                resultado.get('parametros', [])
            )
            tiempo_query = time.time() - inicio_query
            
            if exito:
                print(f"✅ Query ejecutada: {len(resultados)} resultados")
                print(f"⏱️  Tiempo ejecución BD: {tiempo_query:.2f}s")
                print(f"⏱️  TIEMPO TOTAL: {tiempo_sql + tiempo_query:.2f}s")
            else:
                print(f"❌ Error ejecutando query")
        
        print()


def test_sql_especifica():
    """Prueba generación de SQL para consultas específicas."""
    print("="*60)
    print("TEST: Generación SQL - Específica")
    print("="*60)
    
    casos = [
        ("cuantos creditos tiene Redes", "Redes"),
        ("en que curso esta Calculo", "Calculo"),
        ("es obligatoria IS2", "IS2"),
    ]
    
    for pregunta, asignatura in casos:
        print(f"\n📝 Pregunta: '{pregunta}' (asignatura: {asignatura})")
        print("-" * 60)
        
        inicio = time.time()
        resultado = generar_sql_especifica(pregunta, nombre_asignatura=asignatura)
        duracion = time.time() - inicio
        
        print(f"⏱️  Tiempo: {duracion:.2f}s")
        print(f"✅ SQL generada:")
        print(f"   {resultado.get('sql', 'N/A')[:150]}...")
        print(f"📊 Atributo solicitado: {resultado.get('atributo_solicitado', 'N/A')}")
        
        print()


def main():
    print("\n🧪 TEST DE GENERACIÓN TEXT-TO-SQL (Gemini)")
    print("="*60)
    
    # Verificar que Gemini está activo
    if not verificar_gemini_activo():
        print("\n❌ Gemini no está configurado correctamente.")
        print("💡 Verifica que GEMINI_API_KEY esté en el archivo .env")
        return
    
    print()
    
    # Obtener el UUID de la titulación por defecto
    titulacion_id = obtener_titulacion_id()
    if not titulacion_id:
        print("\n⚠️  Ejecutando sin filtro de titulación")
    
    print()
    
    # Test 1: Listados (el que está fallando)
    test_sql_listado(contexto_titulacion=titulacion_id)
    
    # Test 2: Específicas
    #test_sql_especifica()
    
    print("\n" + "="*60)
    print("✅ Tests completados")


if __name__ == "__main__":
    main()
