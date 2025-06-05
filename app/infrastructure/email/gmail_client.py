import os
import base64
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import logging

class GmailAPIClient:
    """Cliente para Gmail API que obtiene emails bancarios usando Desktop App flow"""
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Rutas de archivos de credenciales
        self.credentials_path = credentials_path or 'credentials.json'
        self.token_path = token_path or 'token.json'
        
        # Scopes necesarios para leer y modificar emails (necesario para labels)
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        
        self.service = None
        
        # Configuración de etiquetas
        self.AFP_LABEL_NAME = 'AFP_Processed'
        self.afp_label_id = None
        
        # Bancos aprobados
        self.bank_senders = [
            'notificacion@notificacionesbaccr.com',
            'notify@mail.notion.so',
            'mensajero@bancobcr.com',
            'AlertasScotiabank@scotiabank.com'
        ]
        
        # Configuración temporal
        self.DEFAULT_FIRST_RUN_DAYS = 30  # Primer run: 30 días atrás
        self.DEFAULT_INCREMENTAL_DAYS = 1  # Runs siguientes: 1 día atrás
    
    def authenticate(self) -> bool:
        """Autenticar usando Desktop Application flow (para testing/desarrollo)"""
        try:
            creds = None
            
            # 1. Verificar si ya tenemos token guardado
            if os.path.exists(self.token_path):
                self.logger.info("🔑 Cargando token existente...")
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            
            # 2. Si no hay credenciales válidas, obtener nuevas
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    self.logger.info("🔄 Refrescando token expirado...")
                    creds.refresh(Request())
                else:
                    # 3. Flujo de autorización inicial (abre navegador)
                    if not os.path.exists(self.credentials_path):
                        self.logger.error(f"❌ No se encontró {self.credentials_path}")
                        self.logger.info("📋 Para configurar Gmail API:")
                        self.logger.info("   1. Ve a https://console.cloud.google.com/")
                        self.logger.info("   2. Habilita Gmail API")
                        self.logger.info("   3. Crea credenciales 'Desktop Application'")
                        self.logger.info("   4. Descarga como 'credentials.json'")
                        return False
                    
                    self.logger.info("🌐 Iniciando flujo de autorización (abrirá navegador)...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    
                    # Esto abre el navegador automáticamente
                    creds = flow.run_local_server(port=0)
                
                # 4. Guardar credenciales para la próxima vez
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                    self.logger.info(f"💾 Token guardado en {self.token_path}")
            
            # 5. Crear servicio Gmail
            self.service = build('gmail', 'v1', credentials=creds)
            self.logger.info("✅ Autenticación Gmail API exitosa")
            
            # 6. Configurar label AFP_Processed
            self._setup_afp_label()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error autenticando Gmail API: {str(e)}")
            return False
    
    def _setup_afp_label(self):
        """Crear o encontrar el label AFP_Processed"""
        try:
            # Buscar si ya existe el label
            labels_result = self.service.users().labels().list(userId='me').execute()
            labels = labels_result.get('labels', [])
            
            for label in labels:
                if label['name'] == self.AFP_LABEL_NAME:
                    self.afp_label_id = label['id']
                    self.logger.info(f"✅ Label '{self.AFP_LABEL_NAME}' encontrado: {self.afp_label_id}")
                    return
            
            # Si no existe, crear el label
            label_object = {
                'name': self.AFP_LABEL_NAME,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me', 
                body=label_object
            ).execute()
            
            self.afp_label_id = created_label['id']
            self.logger.info(f"✅ Label '{self.AFP_LABEL_NAME}' creado: {self.afp_label_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error configurando label: {str(e)}")
            self.afp_label_id = None
    
    def add_afp_label_to_email(self, message_id: str) -> bool:
        """Agregar label AFP_Processed a un email"""
        if not self.afp_label_id:
            self.logger.warning("⚠️ No hay label AFP configurado")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [self.afp_label_id]}
            ).execute()
            
            self.logger.debug(f"🏷️ Label agregado a email {message_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error agregando label a {message_id}: {str(e)}")
            return False
    
    def get_last_processed_email_date(self) -> Optional[datetime]:
        """Obtener fecha del último email procesado (con label AFP)"""
        if not self.afp_label_id:
            return None
        
        try:
            # Buscar emails con nuestro label, ordenados por fecha
            results = self.service.users().messages().list(
                userId='me',
                labelIds=[self.afp_label_id],
                maxResults=1
            ).execute()
            
            messages = results.get('messages', [])
            if not messages:
                self.logger.info("📧 No hay emails procesados anteriormente")
                return None
            
            # Obtener fecha del último email procesado
            message = self.service.users().messages().get(
                userId='me',
                id=messages[0]['id'],
                format='metadata',
                metadataHeaders=['Date']
            ).execute()
            
            headers = message['payload'].get('headers', [])
            for header in headers:
                if header['name'] == 'Date':
                    date = self._parse_date(header['value'])
                    self.logger.info(f"📅 Último email procesado: {date}")
                    return date
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo último email procesado: {str(e)}")
            return None
    
    def get_bank_emails(self, since_date: Optional[datetime] = None, max_results: int = 50, 
                        is_first_run: bool = False) -> List[Dict]:
        """Obtener emails bancarios recientes con lógica temporal inteligente"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            # Determinar rango temporal inteligente
            if since_date is None:
                if is_first_run:
                    # Primer run: buscar más atrás
                    since_date = datetime.now() - timedelta(days=self.DEFAULT_FIRST_RUN_DAYS)
                    self.logger.info(f"🕐 Primer run - buscando {self.DEFAULT_FIRST_RUN_DAYS} días atrás")
                else:
                    # Intentar obtener fecha del último email procesado
                    last_processed = self.get_last_processed_email_date()
                    if last_processed:
                        # Buscar desde el último procesado
                        since_date = last_processed
                        self.logger.info(f"🕐 Run incremental - desde último procesado: {since_date}")
                    else:
                        # Fallback: último día
                        since_date = datetime.now() - timedelta(days=self.DEFAULT_INCREMENTAL_DAYS)
                        self.logger.info(f"🕐 Fallback - buscando {self.DEFAULT_INCREMENTAL_DAYS} día(s) atrás")
            
            # Construir query para emails bancarios
            query_parts = []
            
            # Filtrar por remitentes bancarios
            senders_query = ' OR '.join([f'from:{sender}' for sender in self.bank_senders])
            query_parts.append(f'({senders_query})')
            
            # Filtrar por fecha
            date_str = since_date.strftime('%Y/%m/%d')
            query_parts.append(f'after:{date_str}')
            
            # EXCLUIR emails ya procesados (sin nuestro label)
            if self.afp_label_id:
                query_parts.append(f'-label:{self.AFP_LABEL_NAME}')
            
            # Palabras clave financieras (opcional - puede generar ruido)
            keywords = ['transacción', 'compra', 'retiro', 'transferencia', 'pago', 'débito', 'crédito', 'movimiento']
            keywords_query = ' OR '.join(keywords)
            query_parts.append(f'({keywords_query})')
            
            query = ' '.join(query_parts)
            
            self.logger.info(f"🔍 Query optimizada: {query}")
            
            # Buscar mensajes
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            self.logger.info(f"📧 Encontrados {len(messages)} emails bancarios nuevos")
            
            # Obtener detalles de cada mensaje
            emails = []
            for message in messages:
                email_data = self._get_message_details(message['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo emails: {str(e)}")
            return []
    
    def _get_message_details(self, message_id: str) -> Optional[Dict]:
        """Obtener detalles de un mensaje específico"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extraer headers
            headers = message['payload'].get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extraer body
            body = self._extract_body(message['payload'])
            
            # Parsear fecha
            date_str = header_dict.get('Date', '')
            received_date = self._parse_date(date_str)
            
            email_data = {
                'message_id': message_id,
                'gmail_id': message['id'],
                'thread_id': message['threadId'],
                'subject': header_dict.get('Subject', ''),
                'from': header_dict.get('From', ''),
                'to': header_dict.get('To', ''),
                'date': received_date,
                'body': body,
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', []),
                'is_unread': 'UNREAD' in message.get('labelIds', [])
            }
            
            self.logger.debug(f"📄 Email procesado: {email_data['subject'][:50]}...")
            return email_data
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo detalles del mensaje {message_id}: {str(e)}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extraer el body del email"""
        body = ""
        
        if 'parts' in payload:
            # Email multiparte
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
        else:
            # Email simple
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsear fecha del email"""
        try:
            from email.utils import parsedate_tz, mktime_tz
            parsed = parsedate_tz(date_str)
            if parsed:
                timestamp = mktime_tz(parsed)
                return datetime.fromtimestamp(timestamp)
        except Exception as e:
            self.logger.warning(f"⚠️ Error parseando fecha '{date_str}': {str(e)}")
        return None
    
    def test_connection(self) -> bool:
        """Probar conexión con Gmail API"""
        try:
            if not self.authenticate():
                return False
            
            # Hacer una consulta simple
            results = self.service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            
            self.logger.info("✅ Conexión Gmail API funcionando correctamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error probando conexión: {str(e)}")
            return False


# Función de compatibilidad para el código existente
def get_recent_emails(limit=10):
    """Función de compatibilidad que usa Gmail API"""
    client = GmailAPIClient()
    emails = client.get_bank_emails(max_results=limit)
    
    # Convertir formato para compatibilidad
    for email in emails:
        yield {
            "subject": email.get('subject', ''),
            "from": email.get('from', ''),
            "body": email.get('body', ''),
            "message_id": email.get('message_id', ''),
            "date": email.get('date'),
            "gmail_data": email  # Datos completos para debugging
        }
