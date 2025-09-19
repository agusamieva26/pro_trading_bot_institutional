#!/usr/bin/env python3
"""
🏛️ LOCALAI INSTITUTIONAL MULTI-MODEL MANAGER
Advanced Trading AI System with Multiple Specialized Models
- Multi-Model Architecture for Different Trading Functions
- GPU Optimization & Performance Monitoring
- Load Balancing & Failover Systems
- Custom Financial Models Integration
- Real-time Performance Metrics
"""
import os
import json
import asyncio
import aiohttp
import subprocess
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from pathlib import Path

@dataclass
class ModelConfig:
    """Configuration for each specialized model"""
    name: str
    model_id: str
    endpoint: str
    port: int
    gpu_enabled: bool
    context_length: int
    max_tokens: int
    temperature: float
    use_case: str  # sentiment, prediction, risk, news, analysis
    priority: int  # 1-10, higher = more priority
    memory_requirement: int  # MB
    startup_time: float  # seconds
    health_check_url: str
    status: str = "stopped"  # stopped, starting, running, failed, maintenance

@dataclass
class PerformanceMetrics:
    """Real-time performance metrics for models"""
    model_name: str
    requests_per_minute: float
    avg_response_time: float
    success_rate: float
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    error_count: int
    last_request: datetime
    uptime: float

@dataclass
class TradingModelSpec:
    """Specification for trading-specific models"""
    model_type: str  # sentiment, technical, news, risk, prediction
    specialized_for: List[str]  # asset classes: crypto, stocks, forex, commodities
    accuracy_benchmark: float
    latency_requirement: float  # max seconds for response
    concurrent_capacity: int
    training_data_source: str

class LocalAIInstitutionalManager:
    """
    🏛️ Advanced LocalAI Manager for Institutional Trading
    Manages multiple specialized AI models with enterprise features
    """
    
    def __init__(self, base_port: int = 8080):
        self.base_port = base_port
        self.models: Dict[str, ModelConfig] = {}
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.load_balancer_config = {}
        self.gpu_available = self._check_gpu_availability()
        self.config_dir = Path("bot/localai_configs")
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize specialized trading models
        self._initialize_trading_models()
        
        # Performance monitoring
        self.monitoring_active = False
        self.alert_thresholds = {
            "response_time_max": 5.0,  # seconds
            "success_rate_min": 0.95,  # 95%
            "cpu_usage_max": 80.0,     # 80%
            "memory_usage_max": 85.0,  # 85%
        }
        
        logger.info("🏛️ LocalAI Institutional Manager initialized")
    
    def _start_monitoring(self):
        """Inicia el monitoreo de rendimiento de modelos"""
        try:
            self.monitoring_active = True
            logger.info("📊 Performance monitoring started")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            return False

    def _configure_load_balancer(self):
        """Configura el balanceador de carga para modelos"""
        try:
            self.load_balancer_config = {
                "strategy": "round_robin",
                "health_check_interval": 30,
                "timeout": 5.0
            }
            logger.info("⚖️ Load balancer configured")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to configure load balancer: {e}")
            return False
    
    def _check_gpu_availability(self) -> bool:
        """Check if GPU acceleration is available"""
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                gpu_count = torch.cuda.device_count()
                gpu_memory = torch.cuda.get_device_properties(0).total_memory // 1024**3
                logger.info(f"🚀 GPU Available: {gpu_count} devices, {gpu_memory}GB memory")
                return True
            else:
                logger.info("💻 CPU-only mode: No GPU detected")
                return False
        except ImportError:
            logger.info("💻 PyTorch not available - CPU mode only")
            return False
    
    def _initialize_trading_models(self):
        """Initialize specialized trading model configurations"""
        
        # 1. SENTIMENT ANALYSIS MODEL (Financial News)
        self.models["sentiment_financial"] = ModelConfig(
            name="Financial Sentiment Analyzer",
            model_id="nlptown/bert-base-multilingual-uncased-sentiment",
            endpoint="http://localhost:8081",
            port=8081,
            gpu_enabled=self.gpu_available,
            context_length=512,
            max_tokens=100,
            temperature=0.1,  # Low temperature for consistent sentiment
            use_case="sentiment",
            priority=9,
            memory_requirement=2048,
            startup_time=15.0,
            health_check_url="http://localhost:8081/v1/models"
        )
        
        # 2. TECHNICAL ANALYSIS PREDICTOR
        self.models["technical_predictor"] = ModelConfig(
            name="Technical Analysis Predictor",
            model_id="microsoft/DialoGPT-large",
            endpoint="http://localhost:8082",
            port=8082,
            gpu_enabled=self.gpu_available,
            context_length=1024,
            max_tokens=200,
            temperature=0.3,
            use_case="prediction",
            priority=10,  # Highest priority
            memory_requirement=4096,
            startup_time=20.0,
            health_check_url="http://localhost:8082/v1/models"
        )
        
        # 3. RISK ASSESSMENT MODEL
        self.models["risk_analyzer"] = ModelConfig(
            name="Advanced Risk Analyzer",
            model_id="microsoft/DialoGPT-medium",
            endpoint="http://localhost:8083",
            port=8083,
            gpu_enabled=False,  # CPU sufficient for risk analysis
            context_length=2048,
            max_tokens=300,
            temperature=0.2,
            use_case="risk",
            priority=8,
            memory_requirement=3072,
            startup_time=12.0,
            health_check_url="http://localhost:8083/v1/models"
        )
        
        # 4. NEWS IMPACT ANALYZER
        self.models["news_impact"] = ModelConfig(
            name="Market News Impact Analyzer",
            model_id="distilbert-base-uncased",
            endpoint="http://localhost:8084",
            port=8084,
            gpu_enabled=self.gpu_available,
            context_length=512,
            max_tokens=150,
            temperature=0.25,
            use_case="news",
            priority=7,
            memory_requirement=2560,
            startup_time=10.0,
            health_check_url="http://localhost:8084/v1/models"
        )
        
        # 5. MARKET ANALYSIS GENERALIST
        self.models["market_analyst"] = ModelConfig(
            name="General Market Analyst",
            model_id="gpt2",
            endpoint="http://localhost:8085",
            port=8085,
            gpu_enabled=False,
            context_length=1024,
            max_tokens=400,
            temperature=0.4,
            use_case="analysis",
            priority=6,
            memory_requirement=1536,
            startup_time=8.0,
            health_check_url="http://localhost:8085/v1/models"
        )
        
        logger.info(f"🤖 Initialized {len(self.models)} specialized trading models")
    
    async def install_and_configure_all(self) -> bool:
        """
        🚀 Install and configure all models with enterprise features
        """
        logger.info("🏗️ Starting institutional LocalAI installation...")
        
        try:
            # 1. Create configuration files
            await self._create_model_configs()
            
            # 2. Setup Docker Compose for multi-model deployment
            await self._setup_docker_compose()
            
            # 3. Install alternative solutions if Docker unavailable
            if not self._check_docker():
                await self._setup_alternative_installation()
            
            # 4. Start all models with load balancing
            await self._start_all_models()
            
            # 5. Initialize performance monitoring
            self._start_monitoring()
            
            # 6. Setup load balancer  
            self._configure_load_balancer()
            
            # 7. Health checks
            health_status = await self._perform_health_checks()
            
            if health_status["healthy_models"] >= 3:  # At least 3 models working
                logger.info("✅ Institutional LocalAI installation completed successfully!")
                return True
            else:
                logger.warning(f"⚠️ Partial installation: {health_status['healthy_models']} models running")
                return False
                
        except Exception as e:
            logger.error(f"❌ Installation failed: {e}")
            return False
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    async def _create_model_configs(self):
        """Create individual configuration files for each model"""
        logger.info("📁 Creating model configuration files...")
        
        for model_name, config in self.models.items():
            config_file = self.config_dir / f"{model_name}_config.yaml"
            
            config_content = f"""
# LocalAI Configuration for {config.name}
name: {config.model_id}
backend: llama
parameters:
  model: {config.model_id}
  context_size: {config.context_length}
  threads: 4
  f16: true
  low_vram: {not config.gpu_enabled}
  gpu_layers: {35 if config.gpu_enabled else 0}
  temperature: {config.temperature}
  top_k: 40
  top_p: 0.95
  max_tokens: {config.max_tokens}

# Performance settings
batch_size: 8
rope_freq_base: 10000
rope_freq_scale: 1.0

# Security
disable_no_action: true
"""
            
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.debug(f"📄 Created config for {model_name}")
    
    async def _setup_docker_compose(self):
        """Setup Docker Compose for multi-model deployment"""
        logger.info("🐳 Setting up Docker Compose configuration...")
        
        docker_compose = {
            "version": "3.8",
            "services": {}
        }
        
        for model_name, config in self.models.items():
            service_config = {
                "image": "localai/localai:latest-gpu" if config.gpu_enabled else "localai/localai:latest-cpu",
                "container_name": f"localai_{model_name}",
                "ports": [f"{config.port}:8080"],
                "volumes": [
                    f"./bot/localai_configs/{model_name}_config.yaml:/models/config.yaml",
                    "./models:/models"
                ],
                "environment": [
                    f"MODELS_PATH=/models",
                    f"THREADS={psutil.cpu_count()}",
                    f"CONTEXT_SIZE={config.context_length}",
                    "DEBUG=true"
                ],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:8080/v1/models"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                }
            }
            
            if config.gpu_enabled:
                service_config["runtime"] = "nvidia"
                service_config["environment"].append("CUDA_VISIBLE_DEVICES=0")
            
            docker_compose["services"][f"localai_{model_name}"] = service_config
        
        # Add load balancer service
        docker_compose["services"]["nginx_lb"] = {
            "image": "nginx:alpine",
            "container_name": "localai_loadbalancer",
            "ports": ["8080:80"],
            "volumes": ["./bot/localai_configs/nginx.conf:/etc/nginx/nginx.conf"],
            "depends_on": list(docker_compose["services"].keys()),
            "restart": "unless-stopped"
        }
        
        with open(self.config_dir / "docker-compose.yml", 'w') as f:
            import yaml
            yaml.dump(docker_compose, f, default_flow_style=False)
        
        # Create nginx load balancer config
        await self._create_nginx_config()
    
    async def _create_nginx_config(self):
        """Create nginx load balancer configuration"""
        nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream localai_sentiment {
        server localai_sentiment_financial:8080;
    }
    
    upstream localai_prediction {
        server localai_technical_predictor:8080;
    }
    
    upstream localai_risk {
        server localai_risk_analyzer:8080;
    }
    
    upstream localai_news {
        server localai_news_impact:8080;
    }
    
    upstream localai_analysis {
        server localai_market_analyst:8080;
    }
    
    server {
        listen 80;
        
        location /sentiment/ {
            proxy_pass http://localai_sentiment/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /prediction/ {
            proxy_pass http://localai_prediction/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /risk/ {
            proxy_pass http://localai_risk/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /news/ {
            proxy_pass http://localai_news/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /analysis/ {
            proxy_pass http://localai_analysis/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        # Default to prediction model
        location / {
            proxy_pass http://localai_prediction/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
"""
        
        with open(self.config_dir / "nginx.conf", 'w') as f:
            f.write(nginx_config)
    
    async def _setup_alternative_installation(self):
        """Setup alternative installation without Docker"""
        logger.info("🦙 Setting up alternative LocalAI installation (no Docker)...")
        
        # Try Ollama first
        try:
            # Download Ollama
            if os.name != 'nt':  # Unix/Linux
                logger.info("📥 Installing Ollama...")
                result = subprocess.run([
                    'curl', '-fsSL', 'https://ollama.com/install.sh'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    subprocess.run(['sh', '-c', result.stdout], check=True)
                    
                    # Download models
                    for model_name, config in self.models.items():
                        logger.info(f"📥 Downloading {config.model_id}...")
                        subprocess.run(['ollama', 'pull', config.model_id], check=False)
                        
                        # Start model on specific port
                        subprocess.Popen([
                            'ollama', 'serve',
                            '--port', str(config.port),
                            '--model', config.model_id
                        ])
                        
                        await asyncio.sleep(2)  # Brief pause between starts
                    
                    return True
        except Exception as e:
            logger.warning(f"⚠️ Ollama installation failed: {e}")
        
        # Fallback to Python-based models
        logger.info("🐍 Setting up Python-based models as fallback...")
        return await self._setup_python_models()
    
    async def _setup_python_models(self) -> bool:
        """Setup local Python-based models using transformers"""
        try:
            # Install required packages
            subprocess.run([
                'pip', 'install', 'transformers', 'torch', 'tensorflow', 
                'sentence-transformers', 'accelerate'
            ], check=True)
            
            # Create Python model servers
            for model_name, config in self.models.items():
                server_script = self._create_python_model_server(model_name, config)
                
                # Start server in background
                subprocess.Popen([
                    'python', '-c', server_script
                ], env={**os.environ, 'PORT': str(config.port)})
                
                await asyncio.sleep(3)  # Allow startup time
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Python models setup failed: {e}")
            return False
    
    def _create_python_model_server(self, model_name: str, config: ModelConfig) -> str:
        """Create a Python model server script"""
        return f"""
import os
from flask import Flask, request, jsonify
from transformers import pipeline, AutoTokenizer, AutoModel
import torch
from datetime import datetime

app = Flask(__name__)

# Initialize model
model_id = "{config.model_id}"
try:
    if "sentiment" in "{model_name}":
        model = pipeline("sentiment-analysis", model=model_id)
    elif "technical" in "{model_name}" or "prediction" in "{model_name}":
        model = pipeline("text-generation", model=model_id, max_length={config.max_tokens})
    else:
        model = pipeline("text-generation", model=model_id, max_length={config.max_tokens})
    
    print(f"✅ Model {{model_id}} loaded successfully")
except Exception as e:
    print(f"❌ Error loading model: {{e}}")
    model = None

@app.route('/v1/models', methods=['GET'])
def list_models():
    return jsonify({{
        "data": [{{
            "id": model_id,
            "object": "model",
            "created": int(datetime.now().timestamp()),
            "owned_by": "localai"
        }}]
    }})

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    if not model:
        return jsonify({{"error": "Model not available"}}), 500
    
    data = request.json
    messages = data.get('messages', [])
    
    # Extract user message
    user_message = ""
    for msg in messages:
        if msg.get('role') == 'user':
            user_message = msg.get('content', '')
            break
    
    if not user_message:
        return jsonify({{"error": "No user message found"}}), 400
    
    try:
        # Generate response based on model type
        if "sentiment" in "{model_name}":
            result = model(user_message)
            response = f"Sentiment: {{result[0]['label']}} ({{result[0]['score']:.2f}})"
        else:
            result = model(user_message, max_length={config.max_tokens}, 
                         temperature={config.temperature}, do_sample=True)
            response = result[0]['generated_text']
        
        return jsonify({{
            "choices": [{{
                "message": {{"role": "assistant", "content": response}},
                "index": 0,
                "finish_reason": "stop"
            }}],
            "usage": {{"total_tokens": len(user_message.split())}}
        }})
        
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({{"status": "healthy", "model": model_id}})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', {config.port}))
    app.run(host='0.0.0.0', port=port, debug=False)
"""
    
    async def _start_all_models(self):
        """Start all configured models"""
        logger.info("🚀 Starting all LocalAI models...")
        
        if self._check_docker():
            # Use Docker Compose
            compose_file = self.config_dir / "docker-compose.yml"
            result = subprocess.run([
                'docker-compose', '-f', str(compose_file), 'up', '-d'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Docker Compose started successfully")
            else:
                logger.error(f"❌ Docker Compose failed: {result.stderr}")
        
        # Wait for models to start
        await asyncio.sleep(30)
        
        # Verify each model
        for model_name, config in self.models.items():
            try:
                response = requests.get(config.health_check_url, timeout=5)
                if response.status_code == 200:
                    config.status = "running"
                    logger.info(f"✅ {config.name} is running on port {config.port}")
                else:
                    config.status = "failed"
                    logger.warning(f"⚠️ {config.name} health check failed")
            except Exception as e:
                config.status = "failed"
                logger.error(f"❌ {config.name} connection failed: {e}")
    
    async def _perform_health_checks(self) -> Dict[str, Any]:
        """Perform comprehensive health checks on all models"""
        logger.info("🏥 Performing health checks...")
        
        health_status = {
            "healthy_models": 0,
            "failed_models": 0,
            "total_models": len(self.models),
            "details": {}
        }
        
        for model_name, config in self.models.items():
            try:
                # Basic connectivity
                response = requests.get(config.health_check_url, timeout=10)
                
                if response.status_code == 200:
                    # Test actual inference
                    test_response = await self._test_model_inference(model_name, config)
                    
                    if test_response["success"]:
                        health_status["healthy_models"] += 1
                        health_status["details"][model_name] = {
                            "status": "healthy",
                            "response_time": test_response["response_time"],
                            "endpoint": config.endpoint
                        }
                        logger.info(f"✅ {config.name}: HEALTHY ({test_response['response_time']:.2f}s)")
                    else:
                        health_status["failed_models"] += 1
                        health_status["details"][model_name] = {
                            "status": "inference_failed",
                            "error": test_response["error"]
                        }
                        logger.warning(f"⚠️ {config.name}: Inference failed")
                else:
                    health_status["failed_models"] += 1
                    health_status["details"][model_name] = {
                        "status": "unreachable",
                        "http_code": response.status_code
                    }
                    logger.error(f"❌ {config.name}: Unreachable (HTTP {response.status_code})")
                    
            except Exception as e:
                health_status["failed_models"] += 1
                health_status["details"][model_name] = {
                    "status": "connection_failed",
                    "error": str(e)
                }
                logger.error(f"❌ {config.name}: Connection failed - {e}")
        
        return health_status
    
    async def _test_model_inference(self, model_name: str, config: ModelConfig) -> Dict[str, Any]:
        """Test actual model inference capability"""
        start_time = time.time()
        
        # Create test prompts based on model use case
        test_prompts = {
            "sentiment": "The market is showing strong bullish momentum with increasing volume.",
            "prediction": "Based on technical analysis, predict the next move for BTC/USD with current RSI at 45.",
            "risk": "Assess the risk level for a $10,000 position in TSLA with current volatility at 25%.",
            "news": "Analyze the market impact: 'Federal Reserve hints at interest rate cuts in Q4 2024.'",
            "analysis": "Provide a brief market summary for today's trading session."
        }
        
        test_prompt = test_prompts.get(config.use_case, test_prompts["analysis"])
        
        try:
            payload = {
                "model": config.model_id,
                "messages": [{"role": "user", "content": test_prompt}],
                "temperature": config.temperature,
                "max_tokens": 50  # Short test
            }
            
            response = requests.post(
                f"{config.endpoint}/v1/chat/completions",
                json=payload,
                timeout=15
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return {
                        "success": True,
                        "response_time": response_time,
                        "response": result["choices"][0]["message"]["content"][:100]
                    }
            
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "response_time": response_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }

# Initialize global institutional manager
institutional_manager = LocalAIInstitutionalManager()

async def install_institutional_localai() -> bool:
    """
    🚀 Main installation function for institutional LocalAI
    """
    logger.info("🏛️ Installing LocalAI with Institutional Features...")
    return await institutional_manager.install_and_configure_all()

if __name__ == "__main__":
    asyncio.run(install_institutional_localai())