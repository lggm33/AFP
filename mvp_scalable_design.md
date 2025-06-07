# 🚀 MVP SCALABLE DESIGN - AFP EMAIL PROCESSING

## 🎯 PROBLEMA IDENTIFICADO
- Enfoque actual: 1 EmailImportJob por run × usuario
- Con 100 usuarios: ~28,800 jobs/día (insostenible)
- Necesidad: Escalar a 100+ usuarios manteniendo simplicidad

## ✅ SOLUCIÓN PROPUESTA: ESTADO PERSISTENTE + BATCH

### **CAMBIO 1: Integration con Estado Persistente**

```python
# app/models/integration.py (ACTUALIZAR)
class Integration(Base):
    # ... campos existentes ...
    
    # NUEVOS CAMPOS para estado persistente
    import_status = Column(String(50), default="waiting", nullable=False)  # waiting, running, suspended, error
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)  
    run_frequency_minutes = Column(Integer, default=5, nullable=False)
    
    # Estadísticas del día actual
    emails_processed_today = Column(Integer, default=0, nullable=False)
    emails_found_today = Column(Integer, default=0, nullable=False)
    last_error_message = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    # Control de suspensión
    suspend_until = Column(DateTime, nullable=True)  # Para rate limiting
    suspend_reason = Column(String(255), nullable=True)
```

### **CAMBIO 2: EmailImportJob como Batch Summary**

```python
# app/models/email_import_job.py (ACTUALIZAR)
class EmailImportJob(Base):
    # ... campos existentes ...
    
    # NUEVOS CAMPOS para batch processing
    batch_size = Column(Integer, default=0, nullable=False)  # Cuántas integraciones procesó
    total_emails_found = Column(Integer, default=0, nullable=False)  # Sum de todos los usuarios
    total_emails_processed = Column(Integer, default=0, nullable=False)
    processing_duration_seconds = Column(Integer, default=0, nullable=False)
    
    # Detalles por usuario (JSON)
    user_results = Column(JSON, nullable=True)  # {"user_1": {"emails": 5}, "user_2": {"emails": 0}}
```

### **CAMBIO 3: EmailBatchProcessor Service**

```python
# app/services/email_batch_processor.py (NUEVO)
class EmailBatchProcessor:
    def process_ready_integrations(self) -> Dict:
        """Procesar todas las integraciones que están ready para run"""
        
        # 1. Obtener integraciones ready
        ready_integrations = self._get_ready_integrations()
        
        # 2. Crear un solo EmailImportJob para el batch
        batch_job = self._create_batch_job(len(ready_integrations))
        
        # 3. Procesar cada integración
        results = {}
        for integration in ready_integrations:
            try:
                result = self._process_single_integration(integration)
                results[f"user_{integration.user_id}"] = result
                
                # Actualizar estado de la integración
                self._update_integration_state(integration, "waiting", result)
                
            except Exception as e:
                # Marcar integración como error
                self._update_integration_state(integration, "error", {"error": str(e)})
                
        # 4. Finalizar batch job
        self._complete_batch_job(batch_job, results)
        
        return {
            "integrations_processed": len(ready_integrations),
            "total_emails": sum(r.get("emails_found", 0) for r in results.values()),
            "errors": sum(1 for r in results.values() if "error" in r)
        }
    
    def _get_ready_integrations(self) -> List[Integration]:
        """Obtener integraciones ready para procesar"""
        now = datetime.now()
        
        return session.query(Integration).filter(
            Integration.is_active == True,
            Integration.import_status == "waiting",
            or_(
                Integration.next_run_at.is_(None),  # Primera vez
                Integration.next_run_at <= now     # Ya es hora
            ),
            or_(
                Integration.suspend_until.is_(None),  # No suspendida
                Integration.suspend_until <= now      # Suspensión terminó
            )
        ).all()
```

### **CAMBIO 4: Scheduler Optimizado**

```python
# app/jobs/email_scheduler.py (ACTUALIZAR)
class EmailScheduler:
    def process_emails_job(self):
        """Job optimizado que procesa múltiples usuarios en batch"""
        try:
            batch_processor = EmailBatchProcessor()
            results = batch_processor.process_ready_integrations()
            
            self.logger.info(f"✅ Batch procesado: {results}")
            
        except Exception as e:
            self.logger.error(f"❌ Error en batch: {e}")
```

## 📊 ESCALABILIDAD RESULTANTE

### **100 usuarios con nueva arquitectura:**

**Frecuencia de runs:** Cada 5 minutos
**Jobs por día:** ~288 EmailImportJob (batch jobs, no por usuario)  
**Jobs por mes:** ~8,640 jobs
**Reducción:** 99% menos jobs que enfoque anterior

### **Control granular por usuario:**
- Cada Integration mantiene su estado independiente
- Usuarios problemáticos pueden suspenderse individualmente
- Rate limiting por usuario si Gmail API da errores
- Historial detallado en user_results JSON

### **Debugging mantenido:**
- Batch jobs muestran resumen general
- user_results JSON tiene detalles por usuario
- Integration state tracking para debugging individual
- Error handling granular

## 🔄 MIGRACIÓN DESDE ESTADO ACTUAL

### **Paso 1: Actualizar modelos (SIN migraciones)**
```python
# En desarrollo usan Base.metadata.create_all() automático
# Los nuevos campos se agregan directamente a Integration model
# El sistema detecta cambios por hash y recrea tablas automáticamente

# app/models/integration.py (ACTUALIZAR)
class Integration(Base):
    # ... campos existentes ...
    
    # NUEVOS CAMPOS para estado persistente
    import_status = Column(String(50), default="waiting", nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)  
    run_frequency_minutes = Column(Integer, default=5, nullable=False)
    
    # Estadísticas del día actual
    emails_processed_today = Column(Integer, default=0, nullable=False)
    emails_found_today = Column(Integer, default=0, nullable=False)
    last_error_message = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    
    # Control de suspensión
    suspend_until = Column(DateTime, nullable=True)
    suspend_reason = Column(String(255), nullable=True)
```

### **Paso 2: Migrar datos existentes automáticamente**
```python
# Script para inicializar estados en integración existente
def migrate_existing_integration():
    with DatabaseSession() as session:
        integration = session.query(Integration).first()
        if integration:
            integration.import_status = "waiting"
            integration.last_run_at = integration.last_sync
            integration.next_run_at = datetime.now()  # Ready immediately
            integration.run_frequency_minutes = 5
            session.commit()
```

### **Paso 3: Deploy gradual**
- Implementar EmailBatchProcessor
- Actualizar scheduler para usar batch
- Probar con 1 usuario actual
- Monitorear performance y debugging

## 🤖 INTEGRACIÓN COMPLETA CON PARSING JOBS

### **FLUJO COMPLETO: EMAIL IMPORT + PARSING**

```python
# PASO 1: EmailBatchProcessor (Import)
EmailBatchProcessor.process_ready_integrations()
├── Integration.import_status = "running"
├── Obtiene emails de Gmail API
├── Crea EmailParsingJob con status='pending'
├── Integration.import_status = "waiting"
└── EmailImportJob summary con batch results

# PASO 2: TransactionParsingProcessor (Parsing)  
TransactionParsingProcessor.process_pending_emails()
├── Obtiene EmailParsingJob con status='pending'
├── Aplica AI regex patterns
├── Crea Transaction records
├── EmailParsingJob.status = 'success'
└── Actualiza Bank statistics
```

### **COORDINACIÓN ENTRE AMBOS PROCESOS:**

```python
# app/services/email_batch_processor.py (COMPLETO)
class EmailBatchProcessor:
    def process_ready_integrations(self) -> Dict:
        """Procesar integraciones ready + trigger parsing automático"""
        
        # 1. Procesar emails (como antes)
        results = self._process_integrations_batch()
        
        # 2. Si se obtuvieron emails nuevos, trigger parsing
        if results['total_emails'] > 0:
            self._trigger_parsing_if_needed()
            
        return results
        
    def _trigger_parsing_if_needed(self):
        """Trigger parsing automático si hay emails pendientes"""
        from app.services.transaction_parsing_service import TransactionParsingService
        
        with DatabaseSession() as session:
            pending_count = session.query(EmailParsingJob).filter(
                EmailParsingJob.parsing_status == 'pending'
            ).count()
            
            # Si hay 10+ emails pendientes, trigger parsing inmediato
            if pending_count >= 10:
                parsing_service = TransactionParsingService()
                parsing_service.process_pending_emails_batch()
                self.logger.info(f"🤖 Auto-triggered parsing for {pending_count} emails")
```

### **NUEVOS JOBS COORDINADOS:**

```python
# app/jobs/email_scheduler.py (ACTUALIZAR)
class EmailScheduler:
    def start(self):
        # JOB 1: Import emails (cada 5 min)
        self.scheduler.add_job(
            func=self.email_import_job,
            trigger='interval',
            minutes=5,
            id='email_import',
            name='Batch Email Import'
        )
        
        # JOB 2: Parse transactions (cada 10 min)
        self.scheduler.add_job(
            func=self.transaction_parsing_job,
            trigger='interval',
            minutes=10,
            id='transaction_parsing',
            name='AI Transaction Parsing'
        )
        
        # JOB 3: Cleanup old data (cada día)
        self.scheduler.add_job(
            func=self.cleanup_job,
            trigger='interval',
            hours=24,
            id='cleanup',
            name='Database Cleanup'
        )
    
    def email_import_job(self):
        """Import emails usando batch processor"""
        batch_processor = EmailBatchProcessor()
        results = batch_processor.process_ready_integrations()
        self.logger.info(f"✅ Email import: {results}")
    
    def transaction_parsing_job(self):
        """Parse transactions usando AI service"""
        from app.services.transaction_parsing_service import TransactionParsingService
        parsing_service = TransactionParsingService()
        results = parsing_service.process_pending_emails_batch()
        self.logger.info(f"🤖 AI parsing: {results}")
    
    def cleanup_job(self):
        """Limpiar datos antiguos"""
        from app.services.cleanup_service import CleanupService
        cleanup_service = CleanupService()
        results = cleanup_service.cleanup_old_jobs(days=30)
        self.logger.info(f"🧹 Cleanup: {results}")
```

### **MONITORING Y DEBUG:**

```python
# app/services/monitoring_service.py (NUEVO)
class MonitoringService:
    def get_system_status(self) -> Dict:
        """Estado completo del sistema"""
        with DatabaseSession() as session:
            return {
                'integrations': {
                    'total': session.query(Integration).count(),
                    'active': session.query(Integration).filter(Integration.is_active == True).count(),
                    'waiting': session.query(Integration).filter(Integration.import_status == 'waiting').count(),
                    'error': session.query(Integration).filter(Integration.import_status == 'error').count(),
                },
                'emails': {
                    'pending_parsing': session.query(EmailParsingJob).filter(EmailParsingJob.parsing_status == 'pending').count(),
                    'parsed_today': session.query(EmailParsingJob).filter(
                        EmailParsingJob.parsing_status == 'success',
                        EmailParsingJob.processed_at >= datetime.now().replace(hour=0, minute=0, second=0)
                    ).count(),
                },
                'transactions': {
                    'created_today': session.query(Transaction).filter(
                        Transaction.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
                    ).count(),
                }
            }
```

## ✅ VENTAJAS DE ESTA PROPUESTA

1. **📈 Escalable**: 100 usuarios = 288 jobs/día (vs 28,800)
2. **🔧 Control granular**: Estado por integración
3. **🐛 Debugging**: Historial en JSON + Integration state
4. **⚡ Performance**: Batch processing más eficiente
5. **🔄 Rate limiting**: Suspender usuarios problemáticos
6. **📊 Métricas**: Estadísticas por usuario y generales
7. **🧹 Auto-cleanup**: Menos jobs = menos limpieza necesaria

## 🎯 RESULTADO FINAL

- **Escalabilidad**: Ready para 100+ usuarios
- **Simplicidad**: Un job por batch, no por usuario
- **Control**: Estado independiente por integración
- **Debugging**: Información detallada disponible
- **Performance**: Mucho más eficiente 