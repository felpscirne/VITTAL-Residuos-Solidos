from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1']
    app.run(host=host, port=port, debug=debug)