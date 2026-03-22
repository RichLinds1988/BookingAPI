from app import create_app, db
from flask_migrate import Migrate

# This file is used by Flask-Migrate CLI commands
# e.g. flask db init, flask db migrate, flask db upgrade
# Flask needs to know about the app and db to generate migrations
app = create_app()
migrate = Migrate(app, db)
