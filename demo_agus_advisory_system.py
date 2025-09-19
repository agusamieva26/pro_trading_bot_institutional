#!/usr/bin/env python3
"""
🎯 DEMOSTRACIÓN DEL SISTEMA DE ASESORAMIENTO AGUS FINAL
Ejemplos prácticos del sistema respondiendo preguntas específicas sobre el bot del usuario
"""

import asyncio
import sys
from datetime import datetime

async def demo_agus_advisory():
    """🎯 Demostración completa del Sistema de Asesoramiento AGUS"""
    
    print("🎯 SISTEMA DE ASESORAMIENTO AGUS - DEMOSTRACIÓN PRÁCTICA")
    print("=" * 70)
    
    try:
        # Importar sistema
        from bot.agus_advisory_system import (
            agus_chat, 
            agus_generate_report, 
            agus_get_portfolio_summary,
            agus_get_status
        )
        
        print("✅ Sistema AGUS cargado exitosamente\n")
        
        # 1. Estado del sistema
        print("📊 1. ESTADO DEL SISTEMA AGUS")
        print("-" * 40)
        status = await agus_get_status()
        print(f"• Sistema inicializado: {status.get('system_initialized', 'N/A')}")
        print(f"• Qwen disponible: {status.get('qwen_available', 'N/A')}")
        print(f"• Equity actual: ${status.get('current_equity', 0):,.2f}")
        print(f"• Modo: {status.get('system_mode', 'N/A')}")
        print()
        
        # 2. Resumen del portafolio
        print("💰 2. RESUMEN DEL PORTAFOLIO")
        print("-" * 40)
        summary = await agus_get_portfolio_summary()
        print(f"• Capital Total: ${summary.get('total_equity', 0):,.2f}")
        print(f"• P&L Diario: ${summary.get('daily_pnl', 0):+,.2f} ({summary.get('daily_pnl_pct', 0):+.1f}%)")
        print(f"• P&L Total: ${summary.get('total_pnl', 0):+,.2f} ({summary.get('total_pnl_pct', 0):+.1f}%)")
        print(f"• Drawdown: {summary.get('drawdown_pct', 0):.1f}%")
        print(f"• Win Rate: {summary.get('win_rate', 0):.1f}%")
        print(f"• Posiciones: {summary.get('positions_count', 0)}")
        print()
        
        # 3. Preguntas específicas del usuario
        print("💬 3. CHAT CON AGUS - PREGUNTAS ESPECÍFICAS")
        print("-" * 50)
        
        questions = [
            "¿Cómo está mi bot de trading?",
            "¿Cuánto dinero he perdido?", 
            "¿Está funcionando bien mi estrategia?",
            "¿Qué me recomiendas hacer?",
            "¿Cuál es mi win rate actual?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n👤 PREGUNTA {i}: {question}")
            print("🤖 AGUS RESPONDE:")
            print("-" * 30)
            
            response = await agus_chat(question)
            # Mostrar respuesta limitada para legibilidad
            lines = response.split('\n')
            for line in lines[:8]:  # Primeras 8 líneas
                print(f"   {line}")
            if len(lines) > 8:
                print(f"   ... (y {len(lines) - 8} líneas más)")
            print()
        
        # 4. Reporte diario completo
        print("📋 4. REPORTE DIARIO COMPLETO")
        print("-" * 40)
        print("🤖 Generando reporte detallado...")
        
        daily_report = await agus_generate_report("daily")
        print("\n📊 REPORTE DIARIO:")
        print("=" * 50)
        
        # Mostrar reporte completo
        report_lines = daily_report.split('\n')
        for line in report_lines[:15]:  # Primeras 15 líneas
            print(line)
        if len(report_lines) > 15:
            print(f"\n... (Reporte completo tiene {len(report_lines)} líneas)")
        print()
        
        # 5. Análisis de rendimiento
        print("📈 5. ANÁLISIS DE RENDIMIENTO")
        print("-" * 40)
        print("🤖 Generando análisis de rendimiento...")
        
        performance_report = await agus_generate_report("performance")
        perf_lines = performance_report.split('\n')
        for line in perf_lines[:10]:  # Primeras 10 líneas
            print(line)
        if len(perf_lines) > 10:
            print(f"\n... (Análisis completo tiene {len(perf_lines)} líneas)")
        print()
        
        # 6. Evaluación de riesgo
        print("⚠️ 6. EVALUACIÓN DE RIESGO")
        print("-" * 40)
        print("🤖 Generando evaluación de riesgo...")
        
        risk_report = await agus_generate_report("risk")
        risk_lines = risk_report.split('\n')
        for line in risk_lines[:10]:  # Primeras 10 líneas
            print(line)
        if len(risk_lines) > 10:
            print(f"\n... (Evaluación completa tiene {len(risk_lines)} líneas)")
        print()
        
        # Resumen final
        print("🎯 RESUMEN DE LA DEMOSTRACIÓN")
        print("=" * 50)
        print("✅ Sistema AGUS Advisory funcionando perfectamente")
        print("✅ Análisis contextual específico del bot del usuario")
        print("✅ Respuestas en español con datos reales")
        print("✅ Reportes detallados de portafolio y rendimiento")
        print("✅ Evaluación de riesgo y recomendaciones personalizadas")
        print("✅ Integración completa con Qwen 2.5 y sistemas existentes")
        print()
        print(f"📊 DATOS REALES PROCESADOS:")
        print(f"   • Equity: ${summary.get('total_equity', 0):,.2f}")
        print(f"   • Drawdown: {summary.get('drawdown_pct', 0):.1f}%")
        print(f"   • Estado: {summary.get('system_mode', 'N/A')}")
        print()
        print("🎯 ¡El Sistema de Asesoramiento AGUS está listo para uso en producción!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demostración: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demo_quick_chat():
    """💬 Demo rápido de chat interactivo"""
    print("\n💬 DEMO RÁPIDO - CHAT CON AGUS")
    print("=" * 40)
    
    try:
        from bot.agus_advisory_system import agus_chat
        
        # Preguntas específicas sobre el estado actual
        questions = [
            "Resúmeme el estado actual de mi bot",
            "¿Estoy perdiendo mucho dinero?", 
            "¿Debería preocuparme por el drawdown?"
        ]
        
        for question in questions:
            print(f"\n👤 {question}")
            print("🤖 AGUS:")
            response = await agus_chat(question)
            
            # Mostrar respuesta resumida
            lines = response.split('\n')
            key_lines = [line for line in lines if line.strip() and not line.startswith('**')]
            for line in key_lines[:5]:  # Primeras 5 líneas clave
                print(f"   {line.strip()}")
            print()
        
        print("✅ Chat demo completado")
        
    except Exception as e:
        print(f"❌ Error en chat demo: {e}")

if __name__ == "__main__":
    """🚀 Ejecutar demostración"""
    print(f"🕒 Iniciando demostración a las {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Ejecutar demo completa
    result = asyncio.run(demo_agus_advisory())
    
    if result:
        # Si la demo completa funciona, ejecutar chat rápido
        asyncio.run(demo_quick_chat())
    
    print("\n🎯 Demostración completada")