
# MongoDB connection
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure secret key

# MongoDB connection
client = MongoClient('mongodb+srv://umatiyaaziz2004_db_user:lkCvLsRTypDho7Wx@siramik.k3vxnao.mongodb.net/')
db = client['invoice_db']
invoices_collection = db['invoices']
users_collection = db['users']

# Generate invoice number
def generate_invoice_number(user_id):
    last_invoice = invoices_collection.find_one({'user_id': user_id}, sort=[('number', -1)])
    if last_invoice and last_invoice['number'].startswith('G2FEE'):
        last_number = int(last_invoice['number'].replace('G2FEE', ''))
        new_number = f'G2FEE{last_number + 1:03d}'
    else:
        new_number = 'G2FEE001'
    return new_number

# Routes for authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        mobile = data.get('mobile')
        password = data.get('password').encode('utf-8')

        # Check if user already exists
        if users_collection.find_one({'mobile': mobile}):
            return jsonify({'error': 'Mobile number already registered'}), 400

        # Hash password and save user
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        users_collection.insert_one({'mobile': mobile, 'password': hashed_password})
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        mobile = data.get('mobile')
        password = data.get('password').encode('utf-8')

        user = users_collection.find_one({'mobile': mobile})
        if user and bcrypt.checkpw(password, user['password']):
            session['user_id'] = mobile
            return redirect(url_for('index'))
        else:
            return jsonify({'error': 'Invalid mobile number or password'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Main index route (protected)
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# API routes for invoices (user-specific)
@app.route('/api/invoice-number')
def get_invoice_number():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'number': generate_invoice_number(session['user_id'])})

@app.route('/api/invoices', methods=['GET', 'POST'])
def handle_invoices():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    
    if request.method == 'POST':
        data = request.json
        data['user_id'] = user_id
        data['created_at'] = datetime.utcnow()
        result = invoices_collection.insert_one(data)
        data['_id'] = str(result.inserted_id)
        return jsonify({'message': 'Invoice saved successfully', 'id': data['_id']}), 201
    
    invoices = list(invoices_collection.find({'user_id': user_id}))
    for inv in invoices:
        inv['_id'] = str(inv['_id'])
    return jsonify(invoices)

@app.route('/api/invoices/<id>', methods=['GET', 'PUT', 'DELETE'])
def handle_invoice(id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    
    try:
        oid = ObjectId(id)
    except:
        return jsonify({'error': 'Invalid invoice ID'}), 400

    if request.method == 'GET':
        invoice = invoices_collection.find_one({'_id': oid, 'user_id': user_id})
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        invoice['_id'] = str(invoice['_id'])
        return jsonify(invoice)
    
    if request.method == 'PUT':
        data = request.json
        data['user_id'] = user_id
        data['updated_at'] = datetime.utcnow()
        result = invoices_collection.update_one({'_id': oid, 'user_id': user_id}, {'$set': data})
        if result.matched_count == 0:
            return jsonify({'error': 'Invoice not found'}), 404
        return jsonify({'message': 'Invoice updated successfully'})
    
    if request.method == 'DELETE':
        result = invoices_collection.delete_one({'_id': oid, 'user_id': user_id})
        if result.deleted_count == 0:
            return jsonify({'error': 'Invoice not found'}), 404
        return jsonify({'message': 'Invoice deleted successfully'})

@app.route('/api/invoices/search')
def search_invoices():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    name = request.args.get('name', '')
    address = request.args.get('address', '')
    query = {'user_id': user_id}
    
    if name:
        query['name'] = {'$regex': name, '$options': 'i'}
    if address:
        query['address'] = {'$regex': address, '$options': 'i'}
    
    invoices = list(invoices_collection.find(query))
    for inv in invoices:
        inv['_id'] = str(inv['_id'])
    return jsonify(invoices)

if __name__ == '__main__':
    app.run(debug=True)