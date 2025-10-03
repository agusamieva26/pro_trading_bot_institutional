 # Usa una imagen base de Python delgada pero completa.
 FROM python:3.10-slim
 
 # Establece el directorio de trabajo dentro del contenedor.
 WORKDIR /app
 
 # Evita que Python escriba archivos .pyc
 ENV PYTHONDONTWRITEBYTECODE 1
 # Asegura que la salida de Python no se almacene en búfer, para ver los logs en tiempo real.
 ENV PYTHONUNBUFFERED 1
 
 # Instala dependencias del sistema necesarias para algunas librerías de Python.
 RUN apt-get update && apt-get install -y --no-install-recommends \
     build-essential \
     && rm -rf /var/lib/apt/lists/*
 
 # Copia el archivo de requerimientos primero para aprovechar el cache de Docker.
 COPY requirements.txt .
 
 # Instala las dependencias de Python.
 RUN pip install --no-cache-dir -r requirements.txt
 
 # Copia todo el código de la aplicación al directorio de trabajo.
 COPY . .
 
 # Expone los puertos que usará la aplicación:
 # 8080 para el health check de Fly.io
 # 5000 para el dashboard de Streamlit
 EXPOSE 8080 5000
 
 # El comando que se ejecutará cuando el contenedor inicie.
 # Usamos 'run.py' que orquesta todos los componentes del bot.
 CMD ["python", "run.py"]