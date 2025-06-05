#!/usr/bin/env python3
"""
Script para limpiar jobs huérfanos que quedaron en estado "running"
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime
from app.core.database import DatabaseSession
from app.models.email_import_job import EmailImportJob

def cleanup_orphan_jobs():
    """Limpiar jobs que quedaron en estado 'running' sin completed_at"""
    
    with DatabaseSession() as session:
        # Buscar jobs huérfanos
        orphan_jobs = session.query(EmailImportJob).filter(
            EmailImportJob.status == 'running',
            EmailImportJob.completed_at.is_(None)
        ).all()
        
        if not orphan_jobs:
            print("✅ No hay jobs huérfanos para limpiar")
            return
        
        print(f"🧹 Encontrados {len(orphan_jobs)} jobs huérfanos")
        
        # Marcar como fallidos con mensaje explicativo
        for job in orphan_jobs:
            print(f"   Limpiando job ID {job.id} (started: {job.started_at})")
            
            job.status = 'failed'
            job.error_message = 'Job interrumpido - marcado como fallido durante cleanup'
            job.completed_at = datetime.now()
        
        # Guardar cambios
        session.commit()
        print(f"✅ {len(orphan_jobs)} jobs huérfanos limpiados")

def show_job_summary():
    """Mostrar resumen de jobs después del cleanup"""
    with DatabaseSession() as session:
        total_jobs = session.query(EmailImportJob).count()
        completed_jobs = session.query(EmailImportJob).filter(EmailImportJob.status == 'completed').count()
        failed_jobs = session.query(EmailImportJob).filter(EmailImportJob.status == 'failed').count()
        running_jobs = session.query(EmailImportJob).filter(EmailImportJob.status == 'running').count()
        
        print(f"\n📊 RESUMEN DE JOBS DESPUÉS DEL CLEANUP:")
        print(f"   📁 Total: {total_jobs}")
        print(f"   ✅ Completados: {completed_jobs}")
        print(f"   ❌ Fallidos: {failed_jobs}")
        print(f"   🔄 Running: {running_jobs}")

if __name__ == "__main__":
    print("🧹 Cleanup de Jobs Huérfanos")
    print("=" * 40)
    
    cleanup_orphan_jobs()
    show_job_summary()
    
    print("\n✨ Cleanup completado!") 