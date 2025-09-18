from flask import Flask, request, jsonify
from qwen_integration import QwenChat
import os

app = Flask(__name__)
qwen = QwenChat()

LOGS_PATH = "../../logs/"
BOT_PATH = "../../"

def safe_path(path, base):
    abs_path = os.path.abspath(os.path.join(base, path))
    if not abs_path.startswith(os.path.abspath(base)):
        raise Exception("Acceso denegado.")
    return abs_path

@app.route('/')
def index():
    """Página de estado para la API de Qwen."""
    return jsonify({
        "status": "running",
        "message": "Qwen Chat API está activa.",
        "endpoints": {
            "/api/qwen-chat": {
                "methods": ["POST"],
                "description": "Chatea con el modelo Qwen."
            }
        }
    })

@app.route('/api/qwen-chat', methods=['POST'])
def qwen_chat():
    user_message = request.json.get('message', '')
    # Adjunta logs si se solicita en el mensaje
    if ("leer log" in user_message or "error.log" in user_message) and os.path.exists(safe_path("error.log", LOGS_PATH)):
        try:
            log_path = safe_path("error.log", LOGS_PATH)
            with open(log_path, "r") as f:
                logs = f.read()[-3000:]  # Últimas líneas
            user_message += f"\n\nEste es el contenido reciente de error.log:\n{logs}\n"
        except Exception as e:
            return jsonify({'response': f"No se pudo leer el log: {str(e)}"})
    respuesta = qwen.ask(user_message)
    # Aquí podrías agregar lógica para interpretar y ejecutar acciones propuestas por Qwen (crear/modificar archivos, etc.)
    return jsonify({'response': respuesta})

if __name__ == '__main__':
    app.run(port=5000, debug=True)