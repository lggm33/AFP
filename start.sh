#!/bin/bash

# Configurar variable de entorno para psycopg3
export DATABASE_URL="postgresql+psycopg://afp_user:afp_password@localhost:5432/afp_db"

echo "🚀 Iniciando AFP (Aplicación de Finanzas Personales)..."
echo "======================================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para mostrar mensajes con colores
log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Verificar si Docker está instalado y corriendo
echo "📦 Verificando Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    log_error "Docker no está corriendo. Por favor inicia Docker primero."
    exit 1
fi

log_info "Docker está disponible"

# 2. Iniciar PostgreSQL con Docker Compose
echo "🐘 Iniciando base de datos PostgreSQL..."
docker-compose up -d

if [ $? -eq 0 ]; then
    log_info "PostgreSQL iniciado con Docker Compose"
else
    log_error "Error iniciando PostgreSQL con Docker Compose"
    exit 1
fi

# 3. Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
sleep 5

# Verificar conexión a PostgreSQL
for i in {1..30}; do
    if docker-compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
        log_info "PostgreSQL está listo"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "PostgreSQL no respondió después de 30 intentos"
        exit 1
    fi
    echo "   Intento $i/30..."
    sleep 2
done

# 4. Instalar dependencias Python si es necesario
echo "🐍 Verificando dependencias Python..."
if [ ! -d "venv" ]; then
    log_warning "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

if [ $? -eq 0 ]; then
    log_info "Dependencias Python instaladas"
else
    log_error "Error instalando dependencias Python"
    exit 1
fi

# 5. Verificar que la aplicación puede conectarse a la BD
echo "🔍 Verificando conexión a base de datos..."
python -c "
import sys
sys.path.insert(0, '.')
try:
    from app.core.database import init_database
    init_database()
    print('✅ Conexión a base de datos exitosa')
except Exception as e:
    print(f'❌ Error conectando a base de datos: {e}')
    exit(1)
" 2>/dev/null

if [ $? -ne 0 ]; then
    log_error "No se pudo conectar a la base de datos"
    exit 1
fi

# 6. Mostrar información del sistema
echo ""
echo "📊 Estado del sistema:"
echo "   • PostgreSQL: Running (puerto 5432)"
echo "   • Python venv: Activado"
echo "   • Dependencias: Instaladas"
echo "   • Base de datos: Conectada"
echo ""

# 7. Iniciar la aplicación AFP
echo "🎯 Iniciando aplicación AFP..."
echo "   • Gmail API client: Configurado"
echo "   • Email scheduler: Cada 5 minutos"
echo "   • Web server: http://localhost:8000"
echo ""
log_info "AFP iniciándose - presiona Ctrl+C para detener"
echo "======================================================="

# Ejecutar la aplicación
python -m app.main 