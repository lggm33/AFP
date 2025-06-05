"""
Custom exceptions para AFP
"""

class AFPBaseException(Exception):
    """Excepción base para AFP"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class ValidationError(AFPBaseException):
    """Error de validación de datos"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")

class NotFoundError(AFPBaseException):
    """Recurso no encontrado"""
    def __init__(self, message: str, resource_type: str = None):
        self.resource_type = resource_type
        super().__init__(message, "NOT_FOUND")

class AuthenticationError(AFPBaseException):
    """Error de autenticación"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")

class GmailAPIError(AFPBaseException):
    """Error específico de Gmail API"""
    def __init__(self, message: str, gmail_error_code: str = None):
        self.gmail_error_code = gmail_error_code
        super().__init__(message, "GMAIL_API_ERROR")

class EmailParsingError(AFPBaseException):
    """Error al parsear email bancario"""
    def __init__(self, message: str, email_id: str = None):
        self.email_id = email_id
        super().__init__(message, "EMAIL_PARSING_ERROR")

class DatabaseError(AFPBaseException):
    """Error de base de datos"""
    def __init__(self, message: str, sql_error: str = None):
        self.sql_error = sql_error
        super().__init__(message, "DATABASE_ERROR") 