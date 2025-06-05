# REGLA DE CONTEXTO - PROYECTO AFP

## 🎯 PROYECTO ACTUAL
**Aplicación de Finanzas Personales (AFP)** - Sistema que lee emails bancarios automáticamente para extraer y analizar transacciones financieras.

## 🏗️ ARQUITECTURA
- **Patrón**: **SIMPLIFIED LAYERED + EVOLUTIONARY GROWTH** (cambio desde DDD + Clean Architecture)
- **Stack**: Python + Flask + PostgreSQL + SQLAlchemy + IMAPClient
- **Estructura**: 3 capas simplificadas (Models, Services, API) con crecimiento gradual

## 📁 ESTRUCTURA FINAL LIMPIA ✅

```
app/
├── models/              # ✅ ÚNICO lugar para modelos SQLAlchemy (6 modelos)
│   ├── user.py
│   ├── integration.py
│   ├── transaction.py
│   ├── email_import_job.py
│   ├── email_parsing_job.py
│   └── bank.py
├── core/                # ✅ Database + Base SQLAlchemy + exceptions
│   ├── database.py      # Auto-init DB + Base class
│   ├── exceptions.py    # Custom errors
│   └── utils.py         # Shared utilities
├── services/            # 🎯 Business Logic (siguiente paso)
├── repositories/        # 🎯 Data Access genérico (siguiente paso)  
├── infrastructure/      # ✅ SOLO clientes externos
│   └── email/
│       └── gmail_client.py  # Gmail API client
├── jobs/                # ✅ Email scheduler funcionando
│   └── email_scheduler.py
├── api/                 # 🎯 REST endpoints (siguiente paso)
└── main.py              # ✅ App principal funcionando
```

### ✅ LIMPIEZA COMPLETADA
- **Eliminado**: `app/domain/` (modelos duplicados)  
- **Eliminado**: `app/infrastructure/database/` (simplificado a core/database.py)
- **Eliminado**: `app/tasks/`, `app/application/`, `app/config/` (no necesarios)
- **Centralizado**: Base SQLAlchemy en `app/core/database.py`
- **Mantenido**: Solo `app/infrastructure/email/` para Gmail API

## 🚀 Estado Actual (Fase 3 - COMPLETADA + Gmail API)

### ✅ Gmail API Implementado y Funcionando
- **🔐 OAuth2 Desktop Flow**: Autenticación automática con navegador
- **📧 GmailAPIClient**: Cliente completo con filtros bancarios
- **⚙️ EmailService**: Service layer para procesar todos los usuarios
- **🔄 Scheduler Integrado**: APScheduler usando EmailService cada 5 minutos
- **🗃️ Database Tracking**: EmailImportJob y EmailParsingJob funcionando

### ✅ Flujo Completo Gmail 
```
🔄 CADA 5 MINUTOS AUTOMÁTICO:
1. 📅 EmailScheduler ejecuta job
2. 👥 EmailService.process_all_active_users() 
3. 🔑 Para cada integración activa:
   ├── 🌐 GmailAPIClient.authenticate() (usa token.json)
   ├── 📧 gmail.get_bank_emails() (filtros bancarios)
   ├── 💾 Crear EmailImportJob + EmailParsingJob
   ├── 📝 Guardar emails para parsing posterior  
   └── 📊 Actualizar last_sync en Integration
4. 📈 Log resultados completos
```

### ✅ Archivos de Configuración Gmail
- **credentials.json** → Credenciales Desktop App (Google Cloud Console)
- **token.json** → Token OAuth2 guardado automáticamente
- **Ambos en .gitignore** → No se versionan por seguridad

### ✅ Testing Completo
- **5/5 tests pasados** incluyendo Gmail API real
- **Datos de prueba** creados automáticamente  
- **Autenticación OAuth2** funcionando
- **Emails bancarios** siendo obtenidos (0 encontrados porque no hay emails bancarios en la cuenta de prueba)

## 🚧 PRÓXIMOS PASOS - FASE 3: SIMPLIFIED LAYERED ARCHITECTURE

### **CAMBIO DE ESTRATEGIA**: De Clean Architecture → Simplified Layered
**Motivo**: Desarrollo más rápido manteniendo robustez y escalabilidad gradual

### **INFRAESTRUCTURA SIMPLIFICADA**:
- **✅ MANTENER**: Docker + PostgreSQL (ya funciona)
- **🔄 SIMPLIFICAR**: Migraciones → Auto-create tables en desarrollo
- **🎯 RESULTADO**: Un solo comando `./start.sh` para todo

### **1. Core Infrastructure (Simplificado)**
```
app/core/
├── database.py          # Auto-init DB + simplified setup
├── exceptions.py        # Custom exceptions
└── utils.py            # Shared utilities
```

### **2. Repository Layer (Simple & Genérico)**
```
app/repositories/
└── base_repository.py   # CRUD genérico para todos los modelos
```

### **3. Service Layer (Business Logic)**
```
app/services/
├── user_service.py           # Gestión usuarios
├── integration_service.py    # Configuración Gmail  
├── email_service.py          # Procesamiento emails
├── transaction_service.py    # Creación transacciones
└── banking_service.py        # Parsing específico por banco
```

### **4. API Layer (REST Endpoints)**
```
app/api/v1/
├── users.py              # /api/v1/users
├── transactions.py       # /api/v1/transactions
└── integrations.py       # /api/v1/integrations
```

### **5. Simplified Startup (Un solo comando)**
```bash
./start.sh  # Docker + Auto-init DB + Start app
```

## 📚 LECCIONES APRENDIDAS + NUEVAS DECISIONES

### **Infraestructura Simplificada:**
- **Docker + PostgreSQL**: ✅ MANTENER (ya funciona, robustez)
- **Migraciones Alembic**: 🔄 SIMPLIFICAR (solo prod, auto-create en dev)
- **Startup**: Un solo comando `./start.sh` hace todo automáticamente
- **Development Flow**: `Base.metadata.create_all()` en lugar de `alembic upgrade`

### **Arquitectura Evolutiva:**
- **NOW (Simple)**: Models → Services → API (3 capas)
- **LATER (Medium)**: Models → Services → Use Cases → API (4 capas)
- **FUTURE (Complex)**: Domain → Application → Infrastructure → API (Clean Architecture)

### **Ventajas del Cambio:**
- ✅ **50% menos archivos** que Clean Architecture
- ✅ **Development 3x más rápido** 
- ✅ **Mismo nivel de robustez** para el tamaño actual
- ✅ **Escalabilidad gradual** sin reescribir

## 🔗 RELACIONES ENTRE MODELOS - ESTRUCTURA COMPLETADA ✅

### **MODELOS PRINCIPALES (9 TABLAS)**
```
User (1) ──────┬─→ Integration (N)
               │   │
               │   └─→ EmailImportJob (N)
               │       │
               │       └─→ EmailParsingJob (N) ──┬─→ Transaction (N)
               │                                  │
               │                                  └─→ Bank (1)
               │                                      │
               │                                      └─→ ParsingRule (N)
               │
               └─→ TransactionParsingJob (N) [independiente]
               
ProcessingLog [sin FK - solo IDs para audit]
```

### **NUEVOS MODELOS AGREGADOS:**
- ✅ **TransactionParsingJob**: Jobs independientes de parsing
- ✅ **ParsingRule**: Reglas regex específicas por banco  
- ✅ **ProcessingLog**: Audit completo del sistema
- ✅ **Bank (mejorado)**: sender_domains, keywords, parsing_priority

### **ARQUITECTURA DE JOBS CLARIFICADA:**
1. **EmailImportJob**: Obtiene emails de Gmail API (por proveedor)
2. **EmailParsingJob**: Emails individuales pendientes de parsing
3. **TransactionParsingJob**: Job independiente que procesa emails pendientes
4. **ProcessingLog**: Auditoría de todos los procesos

## 🎯 OBJETIVO PRINCIPAL
Extraer automáticamente información de transacciones bancarias desde emails (montos, fechas, descripciones, bancos) y almacenarlas para análisis financiero.

## 📋 REGLAS PARA PRÓXIMAS SESIONES
1. **SIEMPRE** leer este archivo primero para entender el contexto
2. **CONTINUAR** con FASE 3: Simplified Layered Architecture
3. **EMPEZAR** por BaseRepository + UserService como base del patrón
4. **MANTENER** Docker + PostgreSQL pero simplificar desarrollo
5. **USAR** approach evolutivo - crecer gradualmente
6. **SEGUIR** principio "Start Simple, Grow Smart"

## 🔧 COMANDOS ÚTILES (SIMPLIFICADOS)
```bash
# Iniciar entorno completo (TODO EN UNO)
./start.sh

# Solo Docker
docker-compose up -d

# Solo verificar tablas
python -c "from app.models import *; print('Models loaded OK')"

# Reset completo de BD (desarrollo)
docker-compose down -v
docker-compose up -d
./start.sh
```

## 💡 PRÓXIMA SESIÓN RECOMENDADA - EMPEZAR CON:

### **PROPUESTA FINAL APROBADA - MVP RÁPIDO CON GMAIL API**

### **CAMBIOS CONFIRMADOS:**
- ✅ **Arquitectura**: Simplified Layered (Models → Services → API)
- ✅ **Infraestructura**: Docker + PostgreSQL + Auto-init DB
- ✅ **Scheduling**: APScheduler mejorado (cada 5 min)
- 🔄 **NUEVO**: Gmail API en lugar de IMAP (más robusto y seguro)

### **ESTRUCTURA FINAL MVP:**
```
app/
├── models/              # ✅ COMPLETO (9 modelos SQLAlchemy)
│   ├── user.py             # Usuario base
│   ├── integration.py      # Configuración Gmail por usuario
│   ├── email_import_job.py # Jobs de importación por proveedor
│   ├── email_parsing_job.py # Emails individuales pendientes
│   ├── transaction.py      # Transacciones extraídas
│   ├── bank.py            # Bancos con patrones mejorados
│   ├── transaction_parsing_job.py # Jobs independientes parsing
│   ├── parsing_rule.py    # Reglas regex por banco
│   └── processing_log.py  # Audit completo del sistema
├── core/                # 🎯 IMPLEMENTAR
│   ├── database.py      # Auto-init DB simplificado
│   ├── exceptions.py    # Custom errors
│   └── utils.py         # Shared utilities
├── repositories/        # 🎯 IMPLEMENTAR
│   └── base_repository.py  # CRUD genérico
├── services/            # 🎯 IMPLEMENTAR
│   ├── user_service.py     # Gestión usuarios
│   ├── email_service.py    # Procesamiento emails (core del sistema)
│   ├── transaction_service.py # Parsing y creación transacciones
│   └── integration_service.py # Configuración Gmail API
├── infrastructure/      # 🔄 ACTUALIZAR
│   ├── database/        # ✅ Mantener actual
│   └── email/           # 🔄 Cambiar a Gmail API
│       └── gmail_api_client.py  # 🆕 Reemplazar IMAP
├── jobs/                # 🔄 MEJORAR (renombrar desde tasks/)
│   └── email_scheduler.py   # APScheduler mejorado
├── api/                 # 🎯 IMPLEMENTAR
│   └── v1/
│       ├── users.py        # CRUD usuarios
│       ├── integrations.py # Setup Gmail OAuth
│       └── transactions.py # Listar transacciones
└── main.py             # 🔄 SIMPLIFICAR - Un comando para todo
```

### **GMAIL API vs IMAP - VENTAJAS:**
```
IMAP (actual):                    GMAIL API (nuevo):
├── Credenciales usuario/password ├── OAuth2 seguro
├── Conexión directa IMAP         ├── REST API robusta
├── Parsing manual headers        ├── Metadata estructurada
├── Rate limiting unclear         ├── Rate limits claros (250 req/user/sec)
└── Manejo errores básico         └── Error handling avanzado
```

### **IMPLEMENTACIÓN MVP - PLAN 5 DÍAS:**

### **DÍA 1: Core Infrastructure**
- `app/core/database.py` - Auto-init DB simplificado
- `app/core/exceptions.py` - ValidationError, NotFoundError
- `app/repositories/base_repository.py` - Generic CRUD
- Actualizar `./start.sh` - Un comando para todo
- **Resultado**: Base sólida funcionando

### **DÍA 2: Gmail API Integration**
- `app/infrastructure/email/gmail_api_client.py` - Reemplazar IMAP
- Setup OAuth2 credentials y scopes
- `app/services/integration_service.py` - Configurar cuentas Gmail
- **Resultado**: Conexión Gmail API funcionando

### **DÍA 3: User Management + API**
- `app/services/user_service.py` - Business logic usuarios
- `app/api/v1/users.py` - POST/GET users
- `app/api/v1/integrations.py` - Setup Gmail OAuth
- **Resultado**: API básica para crear usuarios y configurar Gmail

### **DÍA 4: Email Processing Core**
- `app/services/email_service.py` - Lógica principal del sistema
- `app/services/transaction_service.py` - Parsing transacciones
- `app/jobs/email_scheduler.py` - APScheduler mejorado
- **Resultado**: Sistema procesando emails automáticamente

### **DÍA 5: Transaction Management + Testing**
- `app/api/v1/transactions.py` - Listar/filtrar transacciones
- Testing completo del flujo
- Logging y monitoring básico
- **Resultado**: MVP completamente funcional

### **FLUJO CORE DEL SISTEMA (LO MÁS IMPORTANTE):**
```
🔄 CADA 5 MINUTOS AUTOMÁTICO:
1. 📧 EmailScheduler ejecuta job
2. 👥 EmailService.process_all_active_users()
3. 🔑 Para cada usuario con Gmail configurado:
   ├── 📞 Gmail API - obtener emails recientes
   ├── 🏦 Filtrar emails bancarios (remitente)
   ├── 💰 TransactionService.parse_transaction()
   ├── 💾 Guardar Transaction en BD
   └── 📊 Actualizar EmailImportJob status
4. 📝 Log resultados + errores
```

### **COMPONENTES GMAIL API ESPECÍFICOS:**
```python
# Gmail API Client
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailAPIClient:
    def get_bank_emails(self, user_credentials, since_date):
        # Usar Gmail API para filtros avanzados
        # query = 'from:(noreply@bancolombia.com.co OR alertas@davivienda.com)'
        # Retornar emails estructurados
        pass
```

### **VENTAJAS MVP CON GMAIL API:**
- ✅ **OAuth2 seguro** - No passwords hardcodeados
- ✅ **Filtros avanzados** - Query Gmail directamente
- ✅ **Rate limiting claro** - 250 req/user/second
- ✅ **Metadata rica** - Headers estructurados
- ✅ **Escalable** - Maneja múltiples usuarios
- ✅ **Monitoring** - Logs detallados
- ✅ **Un solo comando** - `./start.sh` hace todo

### **TECNOLOGÍAS FINALES:**
- **Backend**: Python + Flask + SQLAlchemy
- **Database**: PostgreSQL (Docker)
- **Scheduling**: APScheduler (background threads)
- **Email**: Gmail API + OAuth2
- **Architecture**: Simplified Layered (evolutivo)

### **COMANDOS MVP:**
```bash
# Iniciar todo (desarrollo)
./start.sh

# Health check
curl http://localhost:5000/health

# Crear usuario
curl -X POST http://localhost:5000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Juan","email":"juan@email.com"}'

# Configurar Gmail (OAuth)
curl -X POST http://localhost:5000/api/v1/integrations \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"gmail_oauth_token":"..."}'

# Ver transacciones
curl http://localhost:5000/api/v1/transactions?user_id=1
```

---
**ESTADO**: FASE 2 COMPLETADA ✅ - PROPUESTA FINAL APROBADA 🎯

**PRÓXIMO**: Implementar MVP en 5 días con Gmail API + Simplified Layered Architecture

**ÚLTIMA ACTUALIZACIÓN**: Propuesta final MVP rápido con Gmail API confirmada 