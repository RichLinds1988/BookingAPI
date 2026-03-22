import sys
import os

# Add src/ to path so 'app' and 'config' can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app, db
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)
