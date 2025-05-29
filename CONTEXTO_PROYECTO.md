# REGLA DE CONTEXTO - PROYECTO AFP

## 🎯 PROYECTO ACTUAL
**Aplicación de Finanzas Personales (AFP)** - Sistema que lee emails bancarios automáticamente para extraer y analizar transacciones financieras.

## 🏗️ ARQUITECTURA
- **Patrón**: Domain Driven Design (DDD) + Clean Architecture
- **Stack**: Python + Flask + PostgreSQL + SQLAlchemy + IMAPClient
- **Estructura**: 4 capas bien definidas (Domain, Application, Infrastructure, API)

## 📁 ESTRUCTURA DE DIRECTORIOS
```
app/
├── domain/           # Entidades y reglas de negocio
│   ├── models/      # ✅ COMPLETADO - 6 modelos implementados
│   ├── repositories/ # 🎯 PRÓXIMO - Interfaces de repositorio
│   └── services/    # Servicios de dominio (futuro)
├── application/      # Casos de uso
│   └── use_cases/   # 🎯 PRÓXIMO - Lógica de aplicación
├── infrastructure/   # Implementaciones técnicas
│   ├── database/    # ✅ COMPLETADO - ORM + Migraciones
│   ├── repositories/ # 🎯 PRÓXIMO - Implementaciones concretas
│   └── email/       # Cliente IMAP funcionando
├── api/             # Endpoints REST (futuro)
└── config/          # Configuración
```

## ✅ ESTADO ACTUAL (LO QUE FUNCIONA)

### **FASE 1: MODELOS DE DOMINIO** ✅ COMPLETADO
- **Transaction** (actualizado con trazabilidad)
- **User** (gestión de usuarios)
- **Integration** (configuración Gmail por usuario)
- **EmailImportJob** (tracking de sincronizaciones)
- **EmailParsingJob** (resultado de parsing individual)
- **Bank** (patrones de parsing por banco)

### **FASE 2: INFRAESTRUCTURA DE BASE DE DATOS** ✅ COMPLETADO
- **Modelos ORM SQLAlchemy** completos con relaciones
- **Base de datos PostgreSQL** funcionando con Docker
- **Migraciones Alembic** resueltas y funcionando
- **Todas las tablas creadas** con índices y constraints
- **Relaciones FK** correctamente implementadas

### **OTROS COMPONENTES FUNCIONANDO**
- **Base arquitectónica sólida** con separación de capas
- **Cliente IMAP** funcional para leer emails de Gmail
- **Scheduler** que revisa emails cada 5 minutos
- **Docker Compose** para PostgreSQL

## 🚧 PRÓXIMOS PASOS - FASE 3: REPOSITORIOS

### **1. Interfaces de Repositorio (Domain Layer)**
```
app/domain/repositories/
├── user_repository.py           # Interface UserRepository
├── integration_repository.py    # Interface IntegrationRepository  
├── transaction_repository.py    # Interface TransactionRepository
├── email_import_job_repository.py
├── email_parsing_job_repository.py
└── bank_repository.py
```

### **2. Implementaciones de Repositorio (Infrastructure Layer)**
```
app/infrastructure/repositories/
├── user_repository_impl.py       # Implementación concreta
├── integration_repository_impl.py
├── transaction_repository_impl.py
├── email_import_job_repository_impl.py
├── email_parsing_job_repository_impl.py
└── bank_repository_impl.py
```

### **3. Casos de Uso Básicos (Application Layer)**
```
app/application/use_cases/
├── create_user.py              # Crear usuario
├── create_integration.py       # Configurar cuenta Gmail
├── process_email_import.py     # Procesar sincronización
├── create_transaction.py       # Crear transacción
└── query_transactions.py       # Consultar transacciones
```

### **4. Dependency Injection Setup**
- Configurar inyección de dependencias en `app/main.py`
- Setup de sesiones de BD y repositorios
- Wiring de casos de uso con implementaciones

## 📚 LECCIONES APRENDIDAS HOY

### **Migraciones y Base de Datos:**
- **Docker** crea motor PostgreSQL + BD vacía
- **Alembic** maneja estructura de tablas + versioning
- **Separación clara**: Docker ≠ Migraciones ≠ Aplicación
- **Diagnóstico**: Verificar `alembic current` vs `alembic history` vs archivos
- **Reset completo**: `docker-compose down -v` + `Base.metadata.create_all()`

### **Patrón Repository:**
- **Interface** (Domain): Solo declara QUÉ operaciones (`save()`, `find_by_id()`)
- **Implementation** (Infrastructure): Lógica técnica (ORM, SQL, conversiones)
- **Use Case** (Application): Lógica de negocio (validaciones, reglas)
- **Dependency Injection**: Conexión en `main.py`, no acoplamiento directo

### **Clean Architecture en Práctica:**
- **Dominio**: No depende de nada (entidades + interfaces)
- **Aplicación**: Depende solo del dominio (casos de uso)
- **Infraestructura**: Depende del dominio (implementa interfaces)
- **API**: Depende de aplicación (controllers usan casos de uso)

## 🔗 RELACIONES ENTRE MODELOS
```
User (1) → (N) Integration
Integration (1) → (N) EmailImportJob  
EmailImportJob (1) → (N) EmailParsingJob
EmailParsingJob (1) → (N) Transaction
Bank (1) → (N) EmailParsingJob
```

## 🎯 OBJETIVO PRINCIPAL
Extraer automáticamente información de transacciones bancarias desde emails (montos, fechas, descripciones, bancos) y almacenarlas para análisis financiero.

## 📋 REGLAS PARA PRÓXIMAS SESIONES
1. **SIEMPRE** leer este archivo primero para entender el contexto
2. **CONTINUAR** con FASE 3: Implementación de repositorios
3. **EMPEZAR** por UserRepository como ejemplo del patrón
4. **MANTENER** los principios de DDD y Clean Architecture
5. **USAR** Dependency Injection para conectar capas
6. **SEGUIR** las convenciones de código ya establecidas

## 🔧 COMANDOS ÚTILES
```bash
# Iniciar entorno completo
docker-compose up -d
alembic upgrade head
python app/main.py
./start.sh

# Verificar migraciones
alembic current
alembic history

# Verificar tablas creadas
python -c "from app.infrastructure.database.models import *; from app.infrastructure.database.db import Base; print([t.name for t in Base.metadata.tables.values()])"

# Reset completo de BD (desarrollo)
docker-compose down -v
docker-compose up -d
python -c "from app.infrastructure.database.db import engine, Base; from app.infrastructure.database.models import *; Base.metadata.create_all(bind=engine)"
alembic stamp head
```

## 💡 PRÓXIMA SESIÓN RECOMENDADA - EMPEZAR CON:

### **1. UserRepository (Ejemplo del Patrón)**
- Crear `app/domain/repositories/user_repository.py` (interfaz)
- Crear `app/infrastructure/repositories/user_repository_impl.py` (implementación)
- Crear `app/application/use_cases/create_user.py` (caso de uso)
- Configurar dependency injection en `main.py`

### **Beneficios del enfoque:**
- ✅ **Patrón establecido** para replicar en otros repositorios
- ✅ **Testing** sin base de datos usando mocks
- ✅ **Flexibilidad** para cambiar implementaciones
- ✅ **Separación clara** de responsabilidades

### **Orden sugerido de implementación:**
1. **UserRepository** (base, simple)
2. **IntegrationRepository** (configuración)
3. **TransactionRepository** (consultas complejas)
4. **EmailImportJobRepository** (tracking)
5. **EmailParsingJobRepository** (debugging)
6. **BankRepository** (configuración avanzada)

---
**ESTADO**: FASE 2 COMPLETADA ✅ - Listo para FASE 3: Repositorios 🎯

**ÚLTIMA ACTUALIZACIÓN**: Sesión de implementación de modelos ORM y resolución de migraciones - Base de datos completamente funcional 