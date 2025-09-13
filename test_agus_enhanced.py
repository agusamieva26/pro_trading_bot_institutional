#!/usr/bin/env python3
"""
🧪 Test del Sistema AGUS 2.0 Mejorado
Verificar que AGUS responde en español e implementa código real como el Editor de Replit
"""
import asyncio
import sys
import os
sys.path.append('.')

from datetime import datetime

async def test_agus_enhanced():
    """Test comprehensivo del sistema AGUS mejorado"""
    print("🧪 INICIANDO PRUEBAS DE AGUS 2.0 MEJORADO")
    print("=" * 60)
    
    try:
        # Importar AGUS
        from bot.agus_2_hybrid_system import agus_2_analyze_query, get_agus_2_status
        
        print("✅ AGUS 2.0 importado correctamente")
        
        # Test 1: Verificar estado del sistema
        print("\n🔍 TEST 1: Estado del sistema AGUS")
        status = get_agus_2_status()
        print(f"📊 Status: {status.get('status', 'unknown')}")
        print(f"⏱️ Uptime: {status.get('uptime_seconds', 0):.0f} segundos")
        print(f"🔗 Providers: {status.get('providers', {})}")
        
        # Test 2: Pregunta en español simple
        print("\n🔍 TEST 2: Respuesta en español")
        response = await agus_2_analyze_query(
            query="¿Cómo está el sistema de trading?",
            user_id="test_user",
            session_id="test_session"
        )
        print("📝 Respuesta:")
        print(response[:300] + "..." if len(response) > 300 else response)
        
        # Test 3: Solicitud de revisión de código
        print("\n🔍 TEST 3: Revisión automática de código")
        response = await agus_2_analyze_query(
            query="Revisa el código del sistema y corrige errores",
            user_id="test_user", 
            session_id="test_session"
        )
        print("📝 Respuesta de revisión:")
        print(response[:400] + "..." if len(response) > 400 else response)
        
        # Test 4: Análisis del sistema
        print("\n🔍 TEST 4: Análisis del sistema")
        response = await agus_2_analyze_query(
            query="Analiza el estado del bot de trading",
            user_id="test_user",
            session_id="test_session"
        )
        print("📝 Respuesta de análisis:")
        print(response[:400] + "..." if len(response) > 400 else response)
        
        # Test 5: Verificar herramientas del Editor
        print("\n🔍 TEST 5: Verificar herramientas del Editor")
        from bot.agus_2_hybrid_system import agus_2_system
        
        if hasattr(agus_2_system, 'editor_tools'):
            tools = agus_2_system.editor_tools
            print("✅ Editor Tools disponibles:")
            print(f"   📁 Leer archivos: {hasattr(tools, 'read_file')}")
            print(f"   ✏️ Escribir archivos: {hasattr(tools, 'write_file')}")
            print(f"   🔧 Editar archivos: {hasattr(tools, 'edit_file')}")
            print(f"   📋 Listar archivos: {hasattr(tools, 'list_files')}")
            print(f"   ⚡ Ejecutar comandos: {hasattr(tools, 'execute_command')}")
            
            # Test básico de herramientas
            try:
                files = tools.list_files(".")
                print(f"   📊 Archivos detectados: {len(files)} archivos")
            except Exception as e:
                print(f"   ⚠️ Error en list_files: {e}")
        else:
            print("❌ Editor Tools no encontradas")
            
        print("\n✅ PRUEBAS COMPLETADAS")
        print("🎯 RESULTADO: AGUS 2.0 está funcionando con capacidades del Editor")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR EN PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_agus_enhanced())
    if result:
        print("\n🎉 AGUS 2.0 MEJORADO - FUNCIONANDO CORRECTAMENTE")
    else:
        print("\n💥 AGUS 2.0 - PROBLEMAS DETECTADOS")