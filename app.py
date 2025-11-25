from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / 'data.db'

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

# Simple product catalog for electronics
PRODUCTS = [
	{"id": 1, "name": "Telefon X", "price": 4999, "image": "images/telefon-x.svg"},
	{"id": 2, "name": "Kulaklık Z", "price": 399, "image": "images/kulaklik-z.svg"},
	{"id": 3, "name": "Tablet Pro", "price": 2599, "image": "images/tablet-pro.svg"},
	{"id": 4, "name": "Akıllı Saat S", "price": 899, "image": "images/akilli-saat-s.svg"},
	{"id": 5, "name": "Bluetooth Hoparlör", "price": 249, "image": "images/hoparlor.svg"},
]


def get_db_conn():
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	return conn


def init_db():
	DB_PATH.parent.mkdir(parents=True, exist_ok=True)
	conn = get_db_conn()
	cur = conn.cursor()
	cur.execute('''
	CREATE TABLE IF NOT EXISTS comments (
		id INTEGER PRIMARY KEY,
		product_id INTEGER,
		name TEXT,
		rating INTEGER,
		message TEXT,
		created_at TEXT
	)
	''')
	cur.execute('''
	CREATE TABLE IF NOT EXISTS orders (
		id INTEGER PRIMARY KEY,
		name TEXT,
		email TEXT,
		address TEXT,
		total INTEGER,
		created_at TEXT
	)
	''')
	cur.execute('''
	CREATE TABLE IF NOT EXISTS order_items (
		id INTEGER PRIMARY KEY,
		order_id INTEGER,
		product_id INTEGER,
		qty INTEGER,
		price INTEGER
	)
	''')
	conn.commit()
	conn.close()


init_db()


@app.route('/')
def index():
	return render_template('index.html', products=PRODUCTS)


@app.route('/hakkimizda')
def hakkimizda():
	return render_template('hakkimizda.html')


@app.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
	if request.method == 'POST':
		name = request.form.get('name')
		email = request.form.get('email')
		message = request.form.get('message')
		# In a real app you'd store or send the message. For demo we flash it.
		flash(f"Mesajınız alındı, teşekkürler {name or 'ziyaretçi'}!")
		return redirect(url_for('success'))
	return render_template('iletisim.html')


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
	cart = session.get('cart', {})
	pid = str(product_id)
	cart[pid] = cart.get(pid, 0) + 1
	session['cart'] = cart
	flash('Ürün sepete eklendi.')
	return redirect(url_for('index'))


@app.route('/cart')
def cart():
	cart = session.get('cart', {})
	items = []
	total = 0
	for pid, qty in cart.items():
		prod = next((p for p in PRODUCTS if p['id'] == int(pid)), None)
		if prod:
			subtotal = prod['price'] * qty
			items.append({"product": prod, "qty": qty, "subtotal": subtotal})
			total += subtotal
	return render_template('cart.html', items=items, total=total)


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
	cart = session.get('cart', {})
	pid = str(product_id)
	if pid in cart:
		cart.pop(pid)
		session['cart'] = cart
		flash('Ürün sepetten çıkarıldı.')
	return redirect(url_for('cart'))


@app.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product_detail(product_id):
	prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
	if not prod:
		flash('Ürün bulunamadı.')
		return redirect(url_for('index'))

	conn = get_db_conn()
	cur = conn.cursor()
	if request.method == 'POST':
		name = request.form.get('name') or 'Ziyaretçi'
		rating = int(request.form.get('rating') or 0)
		message = request.form.get('message') or ''
		created_at = datetime.utcnow().isoformat()
		cur.execute('INSERT INTO comments (product_id, name, rating, message, created_at) VALUES (?,?,?,?,?)',
					(product_id, name, rating, message, created_at))
		conn.commit()
		conn.close()
		flash('Yorumunuz kaydedildi.')
		return redirect(url_for('product_detail', product_id=product_id))

	cur.execute('SELECT name, rating, message, created_at FROM comments WHERE product_id = ? ORDER BY created_at DESC', (product_id,))
	comments = cur.fetchall()
	conn.close()
	return render_template('product.html', product=prod, comments=comments)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
	cart = session.get('cart', {})
	items = []
	total = 0
	for pid, qty in cart.items():
		prod = next((p for p in PRODUCTS if p['id'] == int(pid)), None)
		if prod:
			subtotal = prod['price'] * qty
			items.append({"product": prod, "qty": qty, "subtotal": subtotal})
			total += subtotal

	if request.method == 'POST':
		name = request.form.get('name') or 'Müşteri'
		email = request.form.get('email') or ''
		address = request.form.get('address') or ''
		created_at = datetime.utcnow().isoformat()
		conn = get_db_conn()
		cur = conn.cursor()
		cur.execute('INSERT INTO orders (name, email, address, total, created_at) VALUES (?,?,?,?,?)',
					(name, email, address, total, created_at))
		order_id = cur.lastrowid
		for it in items:
			cur.execute('INSERT INTO order_items (order_id, product_id, qty, price) VALUES (?,?,?,?)',
						(order_id, it['product']['id'], it['qty'], it['product']['price']))
		conn.commit()
		conn.close()
		session.pop('cart', None)
		flash('Siparişiniz alındı. Teşekkürler!')
		return render_template('order_success.html', order_id=order_id)

	return render_template('checkout.html', items=items, total=total)


@app.route('/success')
def success():
	return render_template('success.html')


if __name__ == '__main__':
	app.run(debug=True)

