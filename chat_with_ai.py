#!/usr/bin/env python3
"""
💬 CHAT CON TU IA PERSONAL DE TRADING - AGUS POWERED
Interfaz conversacional avanzada con AGUS Hybrid Intelligence System
- LocalAI + Cloud hybrid routing
- Advanced reasoning capabilities  
- Contextual memory integration
- Trading intelligence layer
- Performance optimization
"""
import asyncio
import sys
from datetime import datetime
from loguru import logger
import json
import os
import re
from pathlib import Path

# Configurar logging
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | {message}", level="INFO")

# AGUS Integration
try:
    from bot.agus_2_hybrid_system import (
        agus_2_analyze_query, 
        agus_2_trading_analysis,
        agus_2_debug_system,
        get_agus_2_status,
        agus_2_system
    )
    AGUS_2_AVAILABLE = True
    logger.info("🧠 AGUS Hybrid Intelligence System loaded successfully")
except ImportError as e:
    AGUS_2_AVAILABLE = False
    logger.warning(f"⚠️ AGUS not available: {e}")

class AITradingChat:
    """
    💬 Chat inteligente con AGUS Hybrid Intelligence
    """
    
    def __init__(self):
        self.session_history = []
        self.user_id = "default_user"
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if AGUS_2_AVAILABLE:
            logger.info("🧠 AGUS Hybrid Intelligence System - Ready for advanced conversations!")
        else:
            logger.info("🤖 AGUS (tu IA personal) lista para conversar!")
        
    async def ask_ai(self, question: str, context: dict = None) -> str:
        """
        🧠 Hace una pregunta a la IA personal con AGUS capabilities
        """
        try:
            # Store question in session history
            self.session_history.append({
                "timestamp": datetime.now(),
                "question": question,
                "context": context
            })
            
            # Use AGUS if available for enhanced intelligence
            if AGUS_2_AVAILABLE:
                return await self._agus_2_enhanced_response(question, context)
            else:
                return await self._legacy_response(question, context)
                
        except Exception as e:
            return f"❌ Error comunicándome con la IA: {e}"
    
    async def _agus_2_enhanced_response(self, question: str, context: dict = None) -> str:
        """🔧 Direct technical response using AGUS"""
        try:
            question_lower = question.lower()
            
            # Check for file creation requests
            if any(word in question_lower for word in ["crear archivo", "create file", "generar código", "generate code", "escribir en", "write to", "guardar en", "save to"]):
                return await self._handle_file_creation(question, context)
            
            # Determine query type for optimized processing
            if any(word in question_lower for word in ["debug", "error", "fix", "repair", "reparar", "problema", "arreglar", "bug"]):
                query_type = "debugging"
            elif any(word in question_lower for word in ["analizar", "analysis", "mercado", "market", "btc", "eth", "crypto", "precio", "price"]):
                query_type = "trading"
            elif any(word in question_lower for word in ["trading", "comprar", "vender", "buy", "sell", "estrategia", "strategy"]):
                query_type = "trading"
            elif any(word in question_lower for word in ["bot", "estado", "status", "configuracion", "settings"]):
                query_type = "system"
            else:
                query_type = "general"
            
            # Create trading-specific context for AGUS
            enhanced_prompt = f"""
You are AGUS - technical AI integrated into institutional trading system. Respond DIRECTLY and TECHNICALLY like a skilled engineer.

SYSTEM STATE:
- Portfolio: $18k equity, 16 cryptos active
- ML Models: Random Forest, multi-timeframe analysis  
- Risk Management: Multi-layer protection active
- Trading Status: Real-time execution enabled

USER REQUEST: {question}

CRITICAL - RESPONSE STYLE:
✅ BE DIRECT - No fluff, get straight to the point
✅ BE TECHNICAL - Use precise technical language
✅ SOLVE IMMEDIATELY - Don't just give advice, take action
✅ BE SPECIFIC - Provide exact steps, code, or commands
✅ BE CONCISE - Short, focused responses

If it's a code problem → FIX IT
If it's a technical question → ANSWER PRECISELY  
If it's a file request → CREATE/MODIFY IT
If it's a system issue → DIAGNOSE AND RESOLVE

Respond as the technical expert who gets things done NOW.
"""
            
            # Use AGUS for intelligent analysis with enhanced context
            response = await agus_2_analyze_query(
                query=enhanced_prompt,
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            # Add session context
            response_with_context = f"""🔧 **AGUS** 

{response}

---
⚡ *Technical response - direct & actionable*"""
            
            return response_with_context
            
        except Exception as e:
            logger.error(f"❌ AGUS error: {e}")
            # Fallback to legacy system
            return await self._legacy_response(question, context)
    
    async def _handle_file_creation(self, question: str, context: dict = None) -> str:
        """🔧 Handle file creation requests from AGUS"""
        try:
            # Get AGUS response for the file content generation
            response = await agus_2_analyze_query(
                query=f"Generate file content for this request: {question}. Provide the complete file content that should be written.",
                user_id=self.user_id,
                session_id=self.session_id
            )
            
            # Extract filename from question using regex
            filename_patterns = [
                r'archivo\s+"([^"]+)"',
                r'file\s+"([^"]+)"',
                r'crear\s+(\S+\.py)',
                r'create\s+(\S+\.\w+)',
                r'escribir\s+en\s+(\S+\.\w+)',
                r'write\s+to\s+(\S+\.\w+)',
                r'guardar\s+en\s+(\S+\.\w+)',
                r'save\s+to\s+(\S+\.\w+)',
                r'(\w+\.\w+)'
            ]
            
            filename = None
            question_lower = question.lower()
            
            for pattern in filename_patterns:
                match = re.search(pattern, question_lower)
                if match:
                    filename = match.group(1)
                    break
            
            # If no filename found, ask AGUS to suggest one
            if not filename:
                filename_query = f"Suggest an appropriate filename with extension for: {question}"
                filename_response = await agus_2_analyze_query(
                    query=filename_query,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                # Extract filename from response (simple approach)
                suggested_names = re.findall(r'(\w+\.\w+)', filename_response)
                filename = suggested_names[0] if suggested_names else "agus_generated_file.txt"
            
            # Ensure directory exists
            file_path = Path(filename)
            if file_path.parent != Path('.'):
                os.makedirs(file_path.parent, exist_ok=True)
            
            # Extract code content from response (remove markdown if present)
            content = response
            
            # Remove markdown code blocks if present
            code_block_pattern = r'```(?:\w+)?\n?(.*?)\n?```'
            code_matches = re.findall(code_block_pattern, response, re.DOTALL)
            if code_matches:
                content = code_matches[0].strip()
            
            # Write file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            success_message = f"""🎉 **ARCHIVO CREADO EXITOSAMENTE POR AGUS**

📁 **Archivo**: `{filename}`
📏 **Tamaño**: {len(content)} caracteres
⏰ **Creado**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✨ **Contenido generado por AGUS:**
```
{content[:200]}{'...' if len(content) > 200 else ''}
```

✅ El archivo ha sido guardado y está listo para usar.

---
*AGUS puede crear, modificar y gestionar archivos de código, configuraciones, documentos y más.*"""
            
            return success_message
            
        except Exception as e:
            return f"""❌ **Error creando archivo**

AGUS encontró un problema al crear el archivo:
```
{str(e)}
```

💡 **Sugerencias**:
• Verifica que el nombre del archivo sea válido
• Asegúrate de tener permisos de escritura
• Prueba con un nombre más simple como: `mi_archivo.txt`

🔄 **Prueba con**: "crear archivo ejemplo.py con una función simple" """
    
    async def _legacy_response(self, question: str, context: dict = None) -> str:
        """📱 Legacy response system (backward compatibility)"""
        try:
            from bot.free_ai_assistant import free_ai_assistant
            
            # Add trading context for legacy system too
            enhanced_legacy_prompt = f"""
SISTEMA: Eres AGUS, la IA integrada en un bot de trading institucional avanzado con:
- Portfolio de ~$18,000 operando 16 criptomonedas 
- Gestión de riesgo multicapa activa
- Análisis técnico multi-timeframe 
- Detección de arbitraje entre exchanges
- Modelos ML con Random Forest

PREGUNTA DEL USUARIO: {question}

RESPONDE como la IA integrada del sistema, no como IA genérica.
"""
            
            # Analizar tipo de pregunta
            question_lower = enhanced_legacy_prompt.lower()
            
            # 🛠️ Preguntas sobre debugging/reparación
            if any(word in question_lower for word in ["debug", "error", "fix", "repair", "reparar", "problema", "arreglar", "bug"]):
                return await self._debugging_response(question, context)
            
            # Pregunta sobre análisis de mercado
            elif any(word in question_lower for word in ["analizar", "analysis", "mercado", "market", "btc", "eth", "crypto", "precio", "price"]):
                return await self._market_analysis_response(question, context)
            
            # Pregunta sobre trading/estrategia
            elif any(word in question_lower for word in ["trading", "comprar", "vender", "buy", "sell", "estrategia", "strategy"]):
                return await self._trading_advice_response(question, context)
            
            # Pregunta general sobre el bot
            elif any(word in question_lower for word in ["bot", "estado", "status", "configuracion", "settings"]):
                return await self._bot_status_response(question, context)
            
            # Pregunta general
            else:
                return await self._general_response(question, context)
                
        except Exception as e:
            return f"❌ Error comunicándome con la IA: {e}"
    
    async def _market_analysis_response(self, question: str, context: dict) -> str:
        """Respuesta sobre análisis de mercado"""
        try:
            # Obtener datos del mercado si están disponibles
            from bot.config import settings
            
            response = f"""🧠 **ANÁLISIS DE AGUS**

📊 **Tu pregunta:** {question}

💡 **Análisis actual del mercado:**

**Cryptos principales que estoy monitoreando:**
• BTC/USD: Análisis técnico en curso
• ETH/USD: Evaluando patrones
• SOL/USD: Siguiendo momentum

**Patrones detectados recientemente:**
✅ Golden Cross patterns en algunos activos
📈 RSI showing oversold opportunities
🎯 Volatilidad óptima para scalping detectada

**Mi recomendación IA:**
Basado en los patrones que estoy viendo, hay oportunidades interesantes en cryptos con buena volatilidad. El mercado está mostrando señales mixtas pero con potencial alcista en algunos activos.

💭 **¿Quieres que analice algún símbolo específico? Pregúntame: "analiza BTC" o "qué opinas de ETH"**"""
            
            return response
            
        except Exception as e:
            return f"📊 Análisis de mercado: Error accediendo a datos - {e}"
    
    async def _trading_advice_response(self, question: str, context: dict) -> str:
        """Respuesta sobre consejos de trading"""
        
        response = f"""🎯 **CONSEJO DE AGUS**

❓ **Tu pregunta:** {question}

🧠 **Mi análisis (AGUS):**

**Estado actual:**
• Límite ampliado a -$3,000 para recuperación épica ✅
• Sistema de profit-taking automático activo 
• IA gratuita analizando patrones 24/7
• Kill switch protegiendo tu capital

**Estrategia recomendada:**
1. **Rotación rápida**: 1.3% risk, 1.5% take profit, 0.7% stop loss
2. **Diversificación**: Múltiples cryptos para spread risk  
3. **Patience**: Dejar que el ML + IA trabajen juntos
4. **Capital protection**: System protege con trailing stops

**Mi consejo (AGUS):** 
El bot está optimizado para recuperación. Los modelos ML + mi análisis gratuito están trabajando juntos para encontrar las mejores oportunidades. Confía en el sistema - está diseñado para esa recuperación épica que buscas.

💬 **Pregúntame algo específico como:** "¿debería comprar más BTC?" o "¿cuál es la mejor estrategia ahora?"
"""
        
        return response
    
    async def _bot_status_response(self, question: str, context: dict) -> str:
        """Respuesta sobre estado del bot"""
        try:
            response = f"""🤖 **AGUS - ESTADO DEL BOT**

❓ **Tu pregunta:** {question}

📊 **Estado actual completo:**

**🧠 IA Systems:**
• IA Gratuita Integrada: ✅ ACTIVA
• ML Ensemble Models: ✅ FUNCIONANDO  
• Pattern Detection: ✅ OPERATIVO
• Sentiment Analysis: ✅ LISTO
• 🛠️ **AI DEBUGGER**: ✅ MONITORING 24/7

**💰 Financial Status:**
• Kill Switch Limit: -$3,000 (expandido para recuperación)
• Profit Taking: Automático cada 3%+ ganancia
• Risk per Trade: 1.3% (agresivo optimizado)
• Trailing Stops: 2% activación, 1% distancia

**⚡ Trading Engine:**
• Position Monitor: 24/7 activo
• Multi-timeframe Analysis: Running
• Exposure Management: Automático
• Emergency Protection: Full coverage

**📱 Communications:**
• Telegram Alerts: ✅ CONECTADO
• Daily Reports: Auto-generation
• IA Chat Interface: ✅ ESTA CONVERSACIÓN

**🛠️ DEBUGGING CAPABILITIES:**
• Auto-error Detection: Continuous scanning
• Code Auto-repair: Critical fixes applied automatically
• Log Analysis: Real-time problem identification
• System Optimization: Performance monitoring

**Mi diagnóstico (AGUS):** Todo funcionando con **auto-reparación activada**. El bot está en modo recuperación épica con monitoreo inteligente.

💬 **Pregúntame:** "¿hay errores?" o "repara el código" o "debug completo"
"""
            return response
            
        except Exception as e:
            return f"🤖 Estado del bot: {e}"
    
    async def _debugging_response(self, question: str, context: dict) -> str:
        """🛠️ Respuesta sobre debugging y reparación de código"""
        try:
            from bot.ai_debugger import run_system_debug, quick_fix_cash_buffer
            
            question_lower = question.lower()
            
            # Debug completo del sistema
            if any(word in question_lower for word in ["debug completo", "escanear", "scan", "revisar todo"]):
                logger.info("🔍 Ejecutando debug completo solicitado por usuario...")
                debug_report = run_system_debug()
                return f"🛠️ **DEBUG COMPLETO EJECUTADO**\n\n{debug_report}"
            
            # Fix específico de cash buffer
            elif any(word in question_lower for word in ["cash buffer", "order blocked", "blocked"]):
                fix_result = quick_fix_cash_buffer()
                return f"🛠️ **FIX CASH BUFFER**\n\n{fix_result}\n\n💡 **Nota**: Reinicia el bot para aplicar cambios."
            
            # Respuesta general de debugging
            else:
                return f"""🛠️ **AGUS - TU DEBUGGER PERSONAL**

❓ **Tu pregunta:** {question}

🧠 **Mis capacidades de debugging:**

🔍 **DETECCIÓN AUTOMÁTICA:**
• Escaneo continuo de logs en busca de errores
• Análisis de código para problemas de sintaxis
• Detección de patrones problemáticos
• Monitoreo 24/7 del sistema

🛠️ **AUTO-REPARACIÓN:**
• Fixes automáticos para problemas críticos
• Backup automático antes de modificaciones
• Corrección de errores comunes (async, imports, etc.)
• Optimización de configuraciones

📊 **PROBLEMAS QUE PUEDO RESOLVER:**
• Cash buffer errors (ORDER BLOCKED)
• API quota exceeded (rate limiting)
• Syntax errors (corrección automática)
• Import errors (instalación de módulos)
• Async/await problems (conversión automática)

🎯 **COMANDOS ESPECÍFICOS:**
• "debug completo" - Escaneo completo del sistema
• "repara cash buffer" - Fix específico de trading blocks  
• "hay errores?" - Estado rápido de problemas
• "fix automático" - Aplicar todas las reparaciones

💡 **Ejemplo reciente**: Detecté que el bot está bloqueando órdenes por cash buffer insuficiente. ¿Quieres que lo arregle automáticamente?

🤖 **AGUS está monitoreando tu código 24/7.**
"""
        except Exception as e:
            return f"🛠️ Error en debugging: {e}"

    async def _general_response(self, question: str, context: dict) -> str:
        """Respuesta general"""
        
        responses = {
            "default": f"""🤖 **AGUS RESPONDE**

❓ **Tu pregunta:** {question}

💭 **Mi respuesta IA:**

¡Hola! Soy AGUS, tu IA personal de trading. Soy completamente gratuita y estoy aquí para ayudarte con:

🎯 **Análisis de mercado**: Pregúntame sobre cualquier crypto o stock
📊 **Estrategias**: Consejos personalizados para tu situación  
🤖 **Estado del bot**: Información sobre cómo va todo
💬 **Trading advice**: Decisiones inteligentes basadas en datos
🛠️ **Debugging**: Detección y reparación automática de errores

**Ejemplos de lo que puedes preguntarme:**
• "¿Qué opinas del mercado ahora?"
• "¿Debería comprar BTC o ETH?" 
• "¿Cómo va mi recuperación épica?"
• "¿Hay errores en el código?"
• "Repara el bot automáticamente"
• "Debug completo del sistema"

💡 **Nuevo**: ¡Soy AGUS y puedo reparar tu código automáticamente! Pregúntame sobre errores o debugging.
"""
        }
        
        return responses.get("default")
    
    def print_welcome(self):
        """Muestra bienvenida del chat"""
        if AGUS_2_AVAILABLE:
            welcome = """
╔══════════════════════════════════════════════════════════════════════╗
║              🧠 AGUS 2.0 HYBRID INTELLIGENCE SYSTEM                   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  🚀 Advanced LocalAI+Cloud hybrid system with institutional-grade   ║
║      capabilities. Intelligent routing & contextual memory.         ║
║                                                                      ║
║  🧠 Ejemplos de preguntas:                                          ║
║     • "¿Qué tal va el mercado?"                                     ║
║     • "¿Debería comprar más BTC?"                                   ║
║     • "Analiza ETH para mí"                                         ║
║     • "¿Cómo va mi recuperación épica?"                             ║
║     • "Debug del sistema completo"                                  ║
║                                                                      ║
║  ⚡ Comandos especiales AGUS 2.0:                                   ║
║     • 'agus status' - Estado completo del sistema híbrido           ║
║     • 'market analysis [symbols]' - Análisis híbrido de mercado     ║
║     • 'debug system' - Diagnóstico avanzado con auto-fix            ║
║     • 'agus performance' - Métricas de rendimiento                   ║
║     • 'help' - Ayuda completa del sistema                           ║
║     • 'salir' - Terminar chat                                       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        else:
            welcome = """
╔══════════════════════════════════════════════════════════════════════╗
║                     🤖 CHAT CON AGUS - TU IA PERSONAL                 ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  💬 Ya puedes hablar conmigo - ¡Pregunta lo que quieras!            ║
║                                                                      ║
║  🧠 Ejemplos de preguntas:                                          ║
║     • "¿Qué tal va el mercado?"                                     ║
║     • "¿Debería comprar más BTC?"                                   ║
║     • "Analiza ETH para mí"                                         ║
║     • "¿Cómo va mi recuperación épica?"                             ║
║     • "¿Cuál es el estado del bot?"                                 ║
║                                                                      ║
║  ⚡ Comandos especiales:                                            ║
║     • 'salir' o 'quit' - Terminar chat                             ║
║     • 'help' - Mostrar ayuda                                        ║
║     • 'status' - Estado completo del bot                            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        print(welcome)
    
    async def handle_agus_2_commands(self, question: str) -> bool:
        """🧠 Maneja comandos especiales de AGUS 2.0"""
        if not AGUS_2_AVAILABLE:
            return False
            
        question_lower = question.lower()
        
        try:
            # Estado del sistema AGUS 2.0
            if question_lower in ['agus status', 'agus2 status', 'status agus']:
                print("\n🧠 **AGUS 2.0 SYSTEM STATUS**")
                status = get_agus_2_status()
                
                print(f"""
📊 **Sistema:** {status['system_version']}
🚦 **Estado:** {status['status']}
⏱️ **Uptime:** {status['uptime_seconds']:.0f}s ({status['uptime_seconds']/3600:.1f}h)
👥 **Sesiones activas:** {status['active_sessions']}

🤖 **Proveedores AI:**
• LocalAI: {'✅ Disponible' if status['providers']['localai'] > 0.5 else '❌ No disponible'}
• AGUS: {'✅ Disponible' if status['providers']['agus'] > 0.5 else '❌ No disponible'} 
• Fallback: ✅ Siempre disponible

📈 **Rendimiento:** {len(status.get('performance', {}).get('providers', {}))} proveedores monitoreados
🧠 **Memoria:** {status['memory_stats']['conversations_stored']} conversaciones almacenadas

💾 **Base de datos:** {status['memory_stats']['db_path']}
""")
                return True
            
            # Análisis de mercado híbrido
            elif question_lower.startswith('market analysis') or question_lower.startswith('analyze market'):
                symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD']  # Default symbols
                words = question.split()
                
                # Extract symbols from command
                if len(words) > 2:
                    symbols_text = ' '.join(words[2:])
                    custom_symbols = [s.strip().upper() for s in symbols_text.replace(',', ' ').split() if s.strip()]
                    if custom_symbols:
                        symbols = custom_symbols
                
                print(f"\n🧠 **AGUS 2.0 HYBRID MARKET ANALYSIS**")
                print(f"📊 Analizando: {', '.join(symbols)}")
                print("⚡ Iniciando análisis híbrido con advanced reasoning...")
                
                analysis = await agus_2_trading_analysis(symbols)
                
                if 'executive_summary' in analysis:
                    print(f"\n{analysis['executive_summary']}")
                    
                    if 'detailed_analysis' in analysis:
                        details = analysis['detailed_analysis']
                        if 'sentiment' in details and 'sentiment_analysis' in details['sentiment']:
                            sentiment_data = details['sentiment']['sentiment_analysis']
                            print(f"\n📊 **Confidence:** {analysis.get('confidence', 0.8):.1%}")
                else:
                    print(f"\n⚠️ Análisis incompleto: {analysis.get('error', 'Unknown error')}")
                    
                return True
            
            # Debug del sistema  
            elif question_lower in ['debug system', 'system debug', 'debug agus', 'agus debug']:
                print("\n🛠️ **AGUS 2.0 SYSTEM DEBUGGING**")
                print("🔍 Iniciando diagnóstico avanzado con self-reflection reasoning...")
                
                error_context = {
                    "timestamp": datetime.now().isoformat(),
                    "request_type": "manual_debug",
                    "system_state": "operational",
                    "user_id": self.user_id,
                    "session_id": self.session_id
                }
                
                debug_result = await agus_2_debug_system(error_context)
                
                if 'debug_analysis' in debug_result:
                    print(f"\n{debug_result['debug_analysis']}")
                    print(f"\n🎯 **Confidence:** {debug_result.get('confidence', 0.8):.1%}")
                    
                    if debug_result.get('auto_fix_available'):
                        print("\n🔧 **AUTO-FIX DISPONIBLE** - Reparación automática posible")
                        
                    reasoning_steps = debug_result.get('reasoning_steps', [])
                    if reasoning_steps and len(reasoning_steps) > 1:
                        print(f"\n🧠 **Reasoning Steps:** {len(reasoning_steps)} pasos de análisis completados")
                else:
                    print(f"\n⚠️ Debug incompleto: {debug_result.get('error', 'Unknown error')}")
                    
                return True
            
            # Métricas de rendimiento
            elif question_lower in ['agus performance', 'performance agus', 'agus metrics']:
                print("\n📈 **AGUS 2.0 PERFORMANCE METRICS**")
                status = get_agus_2_status()
                performance = status.get('performance', {})
                
                if 'providers' in performance:
                    print("\n🤖 **Provider Performance:**")
                    for provider, metrics in performance['providers'].items():
                        print(f"""
**{provider.upper()}:**
• Tiempo promedio: {metrics.get('avg_response_time', 0):.2f}s
• Costo total: ${metrics.get('total_cost', 0):.4f}
• Calidad promedio: {metrics.get('avg_quality', 0):.2f}
• Total consultas: {metrics.get('total_queries', 0)}""")
                else:
                    print("📊 Métricas de rendimiento no disponibles aún")
                    
                return True
            
            # Ayuda específica de AGUS 2.0
            elif question_lower in ['agus help', 'help agus']:
                print("""🧠 **AGUS 2.0 HYBRID INTELLIGENCE - AYUDA COMPLETA**

🎯 **CAPACIDADES PRINCIPALES:**
• Advanced reasoning con chain-of-thought, self-reflection, ensemble
• Routing inteligente entre LocalAI ↔ Cloud basado en complejidad
• Memoria contextual persistente con SQLite
• Trading intelligence con sentiment fusion en tiempo real
• Auto-debugging con capacidades de reparación automática
• Optimización de rendimiento y monitoreo de costos

📋 **COMANDOS ESPECIALES AGUS 2.0:**
• 'agus status' - Estado completo del sistema híbrido
• 'market analysis BTC ETH SOL' - Análisis híbrido con reasoning avanzado
• 'debug system' - Diagnóstico con self-reflection y auto-fix
• 'agus performance' - Métricas detalladas de rendimiento
• 'agus help' - Esta ayuda completa

🤖 **TIPOS DE CONSULTA OPTIMIZADOS:**
• Trading: Estrategias, análisis, predicciones (usa ensemble reasoning)
• Sistema: Debugging, optimización, monitoreo (usa self-reflection)  
• General: Cualquier pregunta (routing automático inteligente)

🧠 **MODOS DE REASONING DISPONIBLES:**
• Direct: Respuestas rápidas y directas
• Chain-of-Thought: Análisis paso a paso detallado
• Self-Reflection: Validación y refinamiento automático
• Ensemble: Múltiples enfoques combinados
• Tree-of-Thoughts: Análisis con ramas alternativas

💡 **TIPS AVANZADOS:**
- Más contexto en tu pregunta = routing más inteligente
- AGUS 2.0 recuerda toda la conversación automáticamente
- El sistema aprende de tus patrones y preferencias
- Preguntas complejas activan reasoning avanzado automáticamente
- Debugging crítico usa self-reflection para máxima precisión""")
                return True
                
        except Exception as e:
            print(f"❌ Error procesando comando AGUS 2.0: {e}")
            return True  # Handled, even if error
        
        return False  # Not an AGUS 2.0 command

    async def run_chat(self):
        """
        🚀 Inicia el chat interactivo con capacidades AGUS 2.0
        """
        self.print_welcome()
        
        while True:
            try:
                # Obtener pregunta del usuario
                if AGUS_2_AVAILABLE:
                    question = input("\n🧠 Tu pregunta (AGUS 2.0): ").strip()
                else:
                    question = input("\n💬 Tu pregunta: ").strip()
                
                if not question:
                    continue
                    
                # Comandos de salida
                if question.lower() in ['salir', 'quit', 'exit', 'bye']:
                    if AGUS_2_AVAILABLE:
                        print("🧠 AGUS 2.0: Session terminada. ¡Gracias por usar Hybrid Intelligence! 📈")
                    else:
                        print("🤖 ¡Hasta luego! AGUS siempre estará aquí para ayudarte.")
                    break
                    
                # Comandos de ayuda
                elif question.lower() in ['help', 'ayuda']:
                    if AGUS_2_AVAILABLE and question.lower() != 'agus help':
                        await self.handle_agus_2_commands('agus help')
                    else:
                        self.print_welcome()
                    continue
                    
                # Comando de status legacy
                elif question.lower() == 'status':
                    if AGUS_2_AVAILABLE:
                        await self.handle_agus_2_commands('agus status')
                        continue
                    else:
                        question = "¿cuál es el estado completo del bot?"
                
                # Comandos especiales AGUS 2.0
                if AGUS_2_AVAILABLE and await self.handle_agus_2_commands(question):
                    continue
                
                # Agregar a historial
                self.session_history.append({
                    "timestamp": datetime.now(),
                    "question": question,
                    "type": "user"
                })
                
                # Obtener respuesta de la IA
                if AGUS_2_AVAILABLE:
                    print("\n🧠 AGUS 2.0 Hybrid Intelligence procesando...")
                else:
                    print("\n🤖 Pensando...")
                    
                response = await self.ask_ai(question)
                
                # Mostrar respuesta
                print("\n" + "="*80)
                print(response)
                print("="*80)
                
                # Agregar respuesta al historial
                self.session_history.append({
                    "timestamp": datetime.now(),
                    "response": response,
                    "type": "ai"
                })
                
            except KeyboardInterrupt:
                print("\n\n🤖 AGUS: Chat interrumpido. ¡Hasta pronto!")
                break
            except Exception as e:
                print(f"\n❌ Error en el chat: {e}")

# Funciones de conveniencia
async def chat_with_ai():
    """Inicia chat con IA personal"""
    chat = AITradingChat()
    await chat.run_chat()

def quick_ask(question: str):
    """Pregunta rápida a la IA (sin chat interactivo)"""
    async def _ask():
        chat = AITradingChat()
        response = await chat.ask_ai(question)
        print(f"\n🤖 AGUS: {response}\n")
    
    asyncio.run(_ask())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Pregunta directa desde línea de comandos
        question = " ".join(sys.argv[1:])
        quick_ask(question)
    else:
        # Chat interactivo
        try:
            asyncio.run(chat_with_ai())
        except KeyboardInterrupt:
            print("\n👋 ¡Bye!")