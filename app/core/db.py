import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SQLITE = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

SQL={
    'default': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': 'Tienda',
        'USER': 'SA',
        'PASSWORD': '1234',
        'HOST': 'DESKTOP-ERESCG8\SQL2017',  # Puedes usar 'localhost' o la dirección IP del servidor SQL Server.
        'PORT': '',  # Deja esto en blanco para el puerto predeterminado (1433).
        'OPTIONS': {
            'driver': 'ODBC Driver 13 for SQL Server',  # Nombre del controlador ODBC.
            
        },
    },
}