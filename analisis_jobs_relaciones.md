# 🔍 Análisis de Jobs y Relaciones - AFP System

## 📝 PENDIENTE IDENTIFICADO
- **Email Body Storage**: Los emails no guardan `email_body` - requiere debugging del método `_extract_body()` en Gmail API

---

## 🏗️ Arquitectura Actual de Jobs y Relaciones

### 📊 RELACIONES ACTUALES

```
User (1) ──────┐
               ├─→ Integration (N)
               │   ├─ provider: "gmail" 
               │   ├─ email_account
               │   ├─ access_token/refresh_token
               │   └─ last_sync
               │
               └─→ EmailImportJob (N)
                   ├─ status: pending/running/completed/failed
                   ├─ emails_found/emails_processed
                   ├─ started_at/completed_at
                   └─ error_message
                   │
                   └─→ EmailParsingJob (N) ──┐
                       ├─ email_message_id   │
                       ├─ email_subject      │
                       ├─ email_from         │
                       ├─ email_body (❌ VACÍO)
                       ├─ parsing_status     │
                       ├─ confidence_score   │
                       └─ parsing_attempts   │
                       │                     │
                       └─→ Transaction (N) ──┘
                           ├─ description
                           ├─ amount
                           ├─ date
                           ├─ from_bank/to_bank
                           ├─ confidence_score
                           └─ verification_status

Bank (1) ──────┐
               └─→ EmailParsingJob (N)
                   ├─ parsing_patterns (JSON)
                   ├─ confidence_threshold
                   └─ is_active
```

---

## 🔄 FLUJO ACTUAL DE PROCESAMIENTO

### **1. SCHEDULER AUTOMÁTICO (cada 5 min)**
```
EmailScheduler
├─ process_emails_job() ──→ EmailService.process_all_active_users()
├─ test_connection_job() ──→ Verificar Gmail API
└─ APScheduler background
```

### **2. PROCESAMIENTO POR USUARIO**
```
EmailService._process_user_emails(integration)
├─ 1. Crear EmailImportJob (status='running')
├─ 2. Gmail API: get_bank_emails()
├─ 3. Para cada email: _process_single_email()
│   └─ Crear EmailParsingJob (status='pending')
├─ 4. Agregar label 'AFP_Processed' en Gmail
├─ 5. Actualizar EmailImportJob (status='completed')
└─ 6. Actualizar Integration.last_sync
```

### **3. ESTADO ACTUAL - PENDIENTES**
```
✅ COMPLETO: Import emails → EmailParsingJob (status='pending')
❌ FALTANTE: Parsing emails → Transaction creation
❌ FALTANTE: Parser job independiente
❌ FALTANTE: Bank pattern matching
```

---

## 🎯 ANÁLISIS DE LA PROPUESTA DEL USUARIO

### **FLUJO PROPUESTO:**
1. **Usuario** → múltiples emails (diferentes proveedores)
2. **Por proveedor** → EmailImportJob obtiene emails de senders autorizados  
3. **Parser job INDEPENDIENTE** → revisa EmailParsingJob pendientes
4. **Por cada email** → genera Transaction

### **DIFERENCIAS CON IMPLEMENTACIÓN ACTUAL:**

| **Aspecto** | **Actual** | **Propuesto** |
|-------------|------------|---------------|
| **Parser Job** | Parte de EmailService | Job independiente |
| **Procesamiento** | Secuencial: Import→Parse→Transaction | Desacoplado: Import / Parse / Transaction |
| **Scheduler** | Un job para todo | Múltiples jobs especializados |
| **Estado** | Emails en 'pending' | Parser activo procesando |

---

## 🚨 RELACIONES FALTANTES IDENTIFICADAS

### **1. PARSING JOB INDEPENDIENTE**
```python
# FALTANTE: TransactionParsingJob
class TransactionParsingJob(Base):
    __tablename__ = "transaction_parsing_jobs"
    
    id = Column(Integer, primary_key=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    emails_to_parse = Column(Integer, default=0)
    emails_parsed = Column(Integer, default=0)
    transactions_created = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
```

### **2. BANK PATTERN MATCHING**
```python
# MEJORAR: Bank model necesita más campos
class Bank(Base):
    # FALTANTE:
    sender_domains = Column(JSON)  # ["@bancobcr.com", "@baccr.fi.cr"]
    keywords = Column(JSON)        # ["transacción", "compra", "retiro"]
    parsing_priority = Column(Integer, default=0)  # Orden de matching
```

### **3. PARSING RULES/PATTERNS**
```python
# FALTANTE: ParsingRule model
class ParsingRule(Base):
    __tablename__ = "parsing_rules"
    
    id = Column(Integer, primary_key=True)
    bank_id = Column(Integer, ForeignKey("banks.id"))
    rule_type = Column(String(50))  # amount, date, description
    regex_pattern = Column(Text)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
```

### **4. AUDIT/LOGGING**
```python
# FALTANTE: ProcessingLog model  
class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True)
    job_type = Column(String(50))  # import, parsing, transaction
    job_id = Column(Integer)
    level = Column(String(20))     # INFO, WARNING, ERROR
    message = Column(Text)
    created_at = Column(DateTime)
```

---

## ✅ PROPUESTA DE MEJORA

### **ESTRUCTURA JOBS INDEPENDIENTES:**

```python
# 1. EmailImportScheduler (actual - mejorar)
class EmailImportScheduler:
    def run_every_5_min():
        # Solo importar emails nuevos
        pass

# 2. TransactionParsingScheduler (NUEVO)
class TransactionParsingScheduler:
    def run_every_2_min():
        # Procesar EmailParsingJob pendientes
        # Crear Transaction por cada email
        pass

# 3. HealthCheckScheduler (NUEVO)
class HealthCheckScheduler:
    def run_every_hour():
        # Verificar Gmail API
        # Limpiar jobs huérfanos
        # Logs de salud del sistema
        pass
```

### **SERVICIOS ESPECIALIZADOS:**

```python
# TransactionParsingService (NUEVO)
class TransactionParsingService:
    def process_pending_emails():
        # Obtener EmailParsingJob status='pending'
        # Aplicar regex patterns por banco
        # Crear Transaction
        # Actualizar EmailParsingJob status='success'
        pass
    
    def apply_bank_patterns(email, bank):
        # Pattern matching específico por banco
        pass
```

---

## 🎯 CONCLUSIÓN

### **RELACIONES ACTUALES: ✅ SUFICIENTES**
- User → Integration → EmailImportJob → EmailParsingJob → Transaction
- Bank → EmailParsingJob (para patterns)

### **FALTANTES CRÍTICOS:**
1. **TransactionParsingService** - Procesar emails pendientes
2. **Múltiples schedulers especializados** - En lugar de uno monolítico  
3. **Bank pattern matching mejorado** - Reglas más específicas
4. **Audit logging** - Trazabilidad completa

### **PRÓXIMO PASO RECOMENDADO:**
Implementar **TransactionParsingService** que procese los 50 emails pendientes y cree las transacciones reales. 