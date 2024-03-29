from flask import Flask, render_template, session, g,request
from controllers.admin_controller import admin
from controllers.auth_controller import auth
from flask_login import LoginManager
from models.mqtt import mqtt_client, topic_subscribe
from models.db import db, instance
from datetime import datetime
from models import Read
import json

def create_app() -> Flask:
    app = Flask(__name__, template_folder="./views/",
                static_folder="./static/",
                root_path="./")

    app.config['MQTT_BROKER_URL'] = 'broker.hivemq.com'
    app.config['MQTT_BROKER_PORT'] = 1883
    app.config['MQTT_USERNAME'] = ''  # Set this item when you need to verify username and password
    app.config['MQTT_PASSWORD'] = ''  # Set this item when you need to verify username and password
    app.config['MQTT_KEEPALIVE'] = 5  # Set KeepAlive time in seconds
    app.config['MQTT_TLS_ENABLED'] = False  # If your broker supports TLS, set it True
    app.config["SQLALCHEMY_DATABASE_URI"] = instance

    mqtt_client.init_app(app)

    app.config["TESTING"] = False
    app.config['SECRET_KEY'] = 'generated-secrete-key'
    app.config["SQLALCHEMY_DATABASE_URI"] = instance
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')

    @app.route('/')
    def index():
        return render_template("index.html")

    @mqtt_client.on_connect()
    def handle_connect(client, userdata, flags, rc):
        if rc == 0:
            print('Connected successfully')
            for topic in topic_subscribe:
                mqtt_client.subscribe(topic)  # subscribe topic
        else:
            print('Bad connection. Code:', rc)

    @mqtt_client.on_message()
    def handle_mqtt_message(client, userdata, message):
        data = dict(
            topic=message.topic,
            payload=message.payload.decode()
        )
        if message.topic in ["/pharmhub/leitura"]:
            payload_dict = json.loads(data['payload'])
            temperatura = float(payload_dict.get('temp'))
            humidade = float(payload_dict.get('humidity'))

            with app.app_context():
                read = Read(temperatura=temperatura, humidade=humidade, date_time=datetime.now())
                db.session.add(read)
                db.session.commit()

            print('Received message on topic: {topic} with payload: {payload}'.format(**data))

    return app
