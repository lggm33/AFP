# REGLA DE CONTEXTO - PROYECTO AFP

## 🎯 PROYECTO ACTUAL
**Aplicación de Finanzas Personales (AFP)** - Sistema que lee emails bancarios automáticamente para extraer y analizar transacciones financieras.

## 🏗️ ARQUITECTURA
- **Patrón**: **WORKERS + QUEUE SYSTEM** con arquitectura robusta y escalable
- **Stack**: Python + Flask + PostgreSQL + SQLAlchemy + Gmail API
- **Estructura**: Models + Workers + Queue System + API

## 📁 ESTRUCTURA ACTUAL OPTIMIZADA ✅

```
app/
├── models/              # ✅ COMPLETAMENTE REFACTORIZADO
│   ├── user.py               # Usuario base
│   ├── integration.py        # SOLO configuración (OAuth, frecuencia)
│   ├── email_import_job.py   # TODO el estado + workers control
│   ├── email_parsing_job.py  # Emails individuales (sin ai_model_used)
│   ├── job_queue.py         # NUEVO: Colas para workers
│   ├── transaction.py        # Transacciones extraídas
│   ├── bank.py              # Bancos con patrones
│   ├── parsing_rule.py      # Reglas regex (CON ai_model_used)
│   └── processing_log.py    # Audit del sistema
├── core/                # ✅ Auto-init DB funcionando
│   └── database.py          # Auto-recreación por cambios
├── infrastructure/      # ✅ Gmail API funcionando
│   └── email/
│       └── gmail_client.py  # Gmail API con OAuth2
├── workers/             # 🎯 PRÓXIMO: Implementar workers
├── services/            # 🎯 PRÓXIMO: Business logic
├── api/                 # 🎯 PRÓXIMO: REST endpoints
└── main.py             # ✅ App funcionando
```

## 🚀 Estado Actual (MODELOS REFACTORIZADOS + ARQUITECTURA ROBUSTA)

### ✅ REFACTORIZACIÓN COMPLETADA

**🔧 Responsabilidades Bien Separadas:**

### **📋 Integration (SOLO configuración - 10 campos):**
```python
# CONFIGURACIÓN PURA:
'id', 'user_id', 'provider', 'email_account', 'is_active'
'access_token', 'refresh_token', 'sync_frequency_minutes'  
'created_at', 'updated_at'
```

### **⚙️ EmailImportJob (TODO el estado - 20 campos):**
```python
# CONTROL DE WORKERS:
'status', 'worker_id', 'started_at', 'completed_at', 'timeout_at'

# SCHEDULING:  
'last_run_at', 'next_run_at'

# ESTADÍSTICAS:
'total_runs', 'total_emails_processed', 'emails_processed_last_run'
'emails_found_last_run', 'last_run_duration_seconds'

# ERRORES + AUDITORÍA:
'consecutive_errors', 'error_message', 'run_history' (JSON)
```

### **📧 EmailParsingJob (LIMPIO - sin ai_model_used):**
```python
# PARSING CON REGLAS PRE-GENERADAS:
'email_body', 'parsing_rules_used' (JSON), 'extracted_data' (JSON)
'worker_id', 'parsing_status', 'confidence_score'
```

### **🤖 ParsingRule (AI METADATA donde corresponde):**
```python  
# GENERACIÓN CON AI:
'generation_method', 'ai_model_used', 'ai_prompt_used'
'training_emails_count', 'training_emails_sample' (JSON)
'regex_pattern', 'rule_type', 'priority'
```

### **🔄 JobQueue (COLAS UNIFICADAS):**
```python
# UNA TABLA PARA TODAS LAS COLAS:
'queue_name': "email_import" | "email_parsing" 
'job_type', 'job_data' (JSON), 'priority'
'worker_id', 'status', 'attempts', 'timeout_at'
```

## 🔄 ARQUITECTURA DE WORKERS DISEÑADA

### **FLUJO CORRECTO DEFINIDO:**

```
🤖 AI GENERA REGLAS (una vez por banco):
ParsingRule ← AI analiza emails → genera regex patterns

📧 WORKERS USAN REGLAS (múltiples veces):
Integration → EmailImportJob → EmailParsingJob → Transaction
     ↓              ↓                ↓              ↓
  Worker 1      Worker 2        Worker 3      Worker 4
```

### **4 WORKERS A IMPLEMENTAR:**

1. **Job Detector Worker**
   - Escanea `Integration` con `next_run_at <= now`
   - Crea jobs en `JobQueue(queue_name="email_import")`

2. **Email Import Worker** 
   - Procesa `JobQueue(queue_name="email_import")`
   - Llama Gmail API → Crea `EmailParsingJob`

3. **Parsing Detector Worker**
   - Escanea `EmailParsingJob` con `status="pending"`
   - Crea jobs en `JobQueue(queue_name="email_parsing")`

4. **Transaction Creation Worker**
   - Procesa `JobQueue(queue_name="email_parsing")`
   - Aplica `ParsingRule` → Crea `Transaction`

## 🎯 ESTADO ACTUAL: READY PARA WORKERS

### ✅ **COMPLETADO:**
- **🏗️ Modelos**: Arquitectura robusta con responsabilidades claras
- **🗃️ Base de datos**: Auto-recreación por cambios funcionando  
- **📧 Gmail API**: Cliente OAuth2 funcionando
- **🔄 JobQueue**: Sistema de colas unificado diseñado
- **🤖 AI Flow**: Flujo correcto (AI → ParsingRule, no por email)

### 🎯 **PRÓXIMOS PASOS INMEDIATOS:**

## 🚧 FASE ACTUAL: IMPLEMENTACIÓN DE WORKERS

### ✅ **DÍA 1 COMPLETADO: Worker Framework Base**
```
app/workers/
├── __init__.py                        # ✅ Package exports
├── base_worker.py                     # ✅ Clase base común con threading, logging, error handling
├── job_detector_worker.py             # ✅ Worker 1: EmailImportJob → JobQueue (cada 30s)
├── email_import_worker.py             # ✅ Worker 2: JobQueue → Gmail API → EmailParsingJob
├── parsing_detector_worker.py         # ✅ Worker 3: EmailParsingJob → JobQueue (cada 15s)
├── transaction_creation_worker.py     # ✅ Worker 4: JobQueue → Parsing → Transaction
└── worker_manager.py                  # ✅ Coordina todos los workers + monitoring
```

### **FUNCIONALIDADES IMPLEMENTADAS:**
- **BaseWorker**: Threading, heartbeat, error handling, graceful shutdown
- **JobDetectorWorker**: Detecta EmailImportJobs listos (next_run_at <= now)
- **EmailImportWorker**: Procesa cola email_import, llama Gmail API, crea EmailParsingJobs
- **ParsingDetectorWorker**: Detecta EmailParsingJobs pendientes y los encola
- **TransactionCreationWorker**: Identifica banco, aplica reglas, crea transactions
- **WorkerManager**: Inicia/para workers, monitoring, auto-restart

### **DÍA 2: Email Import Worker**
```
app/workers/
├── email_import_worker.py   # Worker 2: JobQueue → EmailParsingJob
└── app/services/
    └── email_service.py     # Business logic email import
```

### **DÍA 3: Parsing Workers**  
```
app/workers/
├── parsing_detector_worker.py    # Worker 3: EmailParsingJob → JobQueue
├── transaction_creation_worker.py # Worker 4: JobQueue → Transaction
└── app/services/
    ├── parsing_service.py         # Business logic parsing
    └── transaction_service.py     # Business logic transactions
```

### **✅ DÍA 4: INTEGRACIÓN AI COMPLETADA Y FUNCIONANDO**
```
app/services/
├── __init__.py                    # ✅ Package exports
└── ai_rule_generator.py          # ✅ ENHANCED OpenAI integration with retry & validation

app/workers/
└── transaction_creation_worker.py # ✅ Integrado con AI service

requirements.txt                   # ✅ Agregado openai==1.54.3 + httpx==0.27.2
.env                              # ✅ Variables OpenAI configuradas
scripts/                          # ✅ Scripts de testing y setup avanzados
├── test_ai_directly.py           # ✅ Test directo de AI
├── test_scotiabank_ai.py         # ✅ Test específico Scotiabank
├── test_enhanced_ai.py           # ✅ NEW: Test sistema mejorado con retry
├── create_all_banks.py           # ✅ Setup automático de bancos
└── verify_db_data.py             # ✅ Verificación estado DB
```

### **✅ DÍA 5: SISTEMA DE TEMPLATES MÚLTIPLES IMPLEMENTADO**
```
app/models/
└── bank_email_template.py        # ✅ NEW: Modelo para múltiples templates por banco

app/services/
└── bank_template_service.py      # ✅ NEW: Servicio para gestión de templates con AI

app/workers/
└── transaction_creation_worker.py # ✅ UPDATED: Integrado con sistema de templates

scripts/
└── test_template_system.py       # ✅ NEW: Test completo del sistema de templates
```

### **🤖 ENHANCED AI RULE GENERATION SYSTEM:**
- **AIRuleGeneratorService v2**: ✅ Sistema robusto con retry automático y validación
- **Auto-retry mechanism**: ✅ Hasta 3 intentos con prompts mejorados si falla
- **Immediate validation**: ✅ Prueba regex contra emails reales antes de guardar
- **Universal compatibility**: ✅ Funciona con cualquier banco del mundo (no limitado a Costa Rica)
- **Confidence scoring**: ✅ Evalúa calidad y asigna puntajes de confianza
- **Fallback patterns**: ✅ Patrones predefinidos como último recurso
- **Adaptive prompting**: ✅ Prompts que mejoran con cada intento
- **Success rate filtering**: ✅ Solo guarda regex que funcionen (>50% éxito)
- **Comprehensive metadata**: ✅ Tracking completo de generación y validación

### **📋 MULTIPLE BANK EMAIL TEMPLATES SYSTEM:**
- **BankEmailTemplate Model**: ✅ Soporte para múltiples templates por banco
- **Intelligent Template Matching**: ✅ Score-based template selection con patrones de subject/sender/body
- **Transaction Type Detection**: ✅ Templates específicos por tipo (compra, retiro, transferencia, etc.)
- **Auto-Generation with AI**: ✅ Generación automática de templates usando GPT-4
- **Performance Tracking**: ✅ Métricas de éxito, confianza y uso por template
- **Priority System**: ✅ Templates con prioridades auto-optimizadas por rendimiento
- **Validation & Testing**: ✅ Validación automática contra emails de prueba
- **Template Lifecycle**: ✅ Auto-desactivación de templates con bajo rendimiento
- **Universal Extraction**: ✅ Extractors para amount, description, date, merchant, reference
- **Fallback Support**: ✅ Fallback a sistema legacy si templates fallan

### **📊 ESTADO ACTUAL DE DATOS:**
- **24 EmailParsingJobs** de bancos costarricenses reales ✅
- **3 Bancos configurados**: BAC, Scotiabank, BCR ✅
- **7 Parsing Rules generadas por AI**: 
  - BAC Costa Rica: 1 regla (amount)
  - Scotiabank Costa Rica: 6 reglas (amount, date, description, source, from_bank, to_bank)
- **Todas las reglas validadas** contra emails reales ✅
- **AI funcionando perfectamente** con gpt-4o-mini ✅

## 💡 DECISIONES ARQUITECTURALES CLAVE

### **✅ Workers + DB Queues vs Redis:**
- **Elegido**: DB Queues (`JobQueue` table)
- **Motivo**: Simplicidad, consistency, audit trail

### **✅ Una tabla JobQueue vs múltiples:**
- **Elegido**: Una tabla con `queue_name` 
- **Motivo**: Escalabilidad, DRY, monitoreo unificado

### **✅ AI en ParsingRule vs EmailParsingJob:**
- **Elegido**: AI metadata en `ParsingRule`
- **Motivo**: AI genera reglas una vez, se usan múltiples veces

### **✅ Estado en EmailImportJob vs Integration:**
- **Elegido**: Estado en `EmailImportJob`
- **Motivo**: `Integration` = configuración, `Job` = estado operacional

## 🔧 COMANDOS PARA CONFIGURAR

### **Iniciar aplicación:**
```bash
./start.sh
```

### **Configurar API Key de OpenAI:**
```bash
# Editar .env y reemplazar your_openai_api_key_here con tu API key real
nano .env
# O usando sed:
sed -i '' 's/your_openai_api_key_here/sk-your-actual-api-key/' .env
```

### **Variables de entorno configuradas:**
```bash
DATABASE_URL=postgresql+psycopg://afp_user:afp_password@localhost:5432/afp_db
OPENAI_API_KEY=your_openai_api_key_here  # ⚠️ REEMPLAZAR CON TU API KEY
OPENAI_MODEL=gpt-4o-mini                # Modelo económico y eficiente
# Iniciar PostgreSQL
docker-compose up -d

# Recrear BD con cambios de modelos (automático)
python -c "from app.core.database import init_database; init_database()"

# Verificar modelos
python -c "from app.models import *; print('✅ Todos los modelos cargados')"

# Próximo: Iniciar workers (a implementar)
python worker_startup.py
```

## 📋 REGLAS PARA PRÓXIMAS SESIONES

1. **IMPLEMENTAR**: Sistema de workers completo (4 workers)
2. **USAR**: JobQueue para todas las colas (email_import, email_parsing)
3. **MANTENER**: Arquitectura limpia (configuración vs estado)
4. **PRINCIPIO**: "AI genera reglas → Workers usan reglas"
5. **TESTING**: Cada worker debe ser testeable independientemente

---
**ESTADO**: MODELOS REFACTORIZADOS ✅ - READY PARA WORKERS 🎯

**PRÓXIMO**: Implementar sistema de workers (4 workers + framework base)

**ÚLTIMA ACTUALIZACIÓN**: Arquitectura robusta con responsabilidades claras 