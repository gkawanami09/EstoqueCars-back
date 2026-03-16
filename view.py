from flask import Flask, jsonify, request, Response, make_response
from flask_bcrypt import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os 
from main import app, con

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/cadastro',methods=[''])
def cadastro():


@app.route('/login', methods=[''])
def login():
    