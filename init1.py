#Import Flask Library
import datetime
from math import trunc

from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors

#for uploading photo:
from app import app
from mysql.connector.constants import flag_is_set
#from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename

import mysql.connector

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash


ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


###Initialize the app from Flask
##app = Flask(__name__)
##app.secret_key = "secret key"

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       password='root',
                       db='FlaskDemo',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


@app.route('/')
def index():
    return render_template('index.html')


#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/login', methods=['GET', 'POST'])
def loginAuth():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = conn.cursor()
        error = None
        cursor.execute(
            'SELECT * FROM Person WHERE username = %s', (username,)
        )
        user = cursor.fetchone()
        if user is None:
            error = 'Non-existing username'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session['username'] = username
            return redirect(url_for('home'))  # change to your main page here
        flash(error)

    return render_template('login.html')

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        role = request.form['role']
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Person WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        error = None
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif (not first_name) or (not last_name):
            error = 'Name is required.'
        elif not email:
            error = 'Email Address is required.'
        elif not role:
            error = 'Role is required.'
        elif existing_user:
            error = f"User {username} is already registered."

        if error is None:
            try:
                cursor.execute(
                    "INSERT INTO Person (username,password,fname,lname,email) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    ( username, generate_password_hash(password), first_name,last_name,email ),
                )
                cursor.execute(
                    "INSERT INTO Act (username,roleID) "
                    "VALUES (%s, %s)",
                    (username, role),
                )
                conn.commit()
                cursor.close()
                flash("You have successfully created the account. Please log in.")
                return redirect(url_for('loginAuth'))
            except mysql.connector.IntegrityError:
                error = f"User {username} is already registered."
        flash(error)
    return render_template('register.html')

@app.route('/finditem', methods=['GET', 'POST'])
def finditem():
    if request.method == 'POST':
        itemID = request.form['itemID']
        cursor = conn.cursor();
        query = 'SELECT * From Item Natural Join Donatedby WHERE itemID = %s and availability = 1 and accepted = 1'
        cursor.execute(query, (itemID))
        data = cursor.fetchall()
        if not data:
            flash("There is no such item available in the stock or this item is not accepted by a staff.")
            return render_template('finditem.html', search = False)
        query2 = 'SELECT * From Piece where itemID = %s'
        cursor.execute(query2, (itemID))
        locations = cursor.fetchall()
        cursor.close()
        return render_template('finditem.html', item=data , search = True,  locations = locations )
    return render_template('finditem.html', search = False)

@app.route('/findorder', methods=['GET', 'POST'])
def findorder():
    if request.method == 'POST':
        orderID = request.form['orderID']
        cursor = conn.cursor();
        query = 'SELECT itemID,pDescription as PieceName, mainCategory, subCategory, roomNum, shelfNum FROM ItemIn NATURAL JOIN Piece NATURAL JOIN Item where orderID = %s order by itemID asc;'
        cursor.execute(query, (orderID))
        data = cursor.fetchall()
        if not data:
            query2 = 'SELECT itemID, mainCategory, subCategory FROM ItemIn NATURAL JOIN Item where orderID = %s order by itemID asc;'
            cursor.execute(query2, (orderID))
            data2 = cursor.fetchall()
            if not data2:
                flash("There is no such order in our record or this order does not contain any item yet.")
                return render_template('findorder.html', search = False)
            cursor.close()
            return render_template('findorder.html', order=data2, search=True)
        cursor.close()
        return render_template('findorder.html', order=data, search = True )
    return render_template('findorder.html', search = False)

@app.route('/accept', methods=['GET', 'POST'])
def accept():
    user = session['username']
    cursor = conn.cursor();
    query = 'SELECT roleID From Act WHERE username = %s and roleID = 1'
    cursor.execute(query, (user))
    data = cursor.fetchone()
    if not data:
        flash("You have to be a staff to accept the donation!")
        return redirect(url_for('home'))
    query2 = 'SELECT * From Donatedby where accepted = 0'
    cursor.execute(query2)
    data2 = cursor.fetchall()

    if request.method == 'POST':
        if request.form.get('pending') is None:
            flash("You have to accept a donor to proceed!")
            return render_template('accept.html', pending=data2)
        accepted = request.form['pending']
        cursor = conn.cursor();
        query = 'Update Donatedby Set accepted = 1 WHERE itemID = %s '
        cursor.execute(query, (accepted))
        conn.commit()
        cursor.close()
        flash("You have successfully accepted the donation.")
        return redirect(url_for('home'))
    return render_template('accept.html', pending = data2)

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    user = session['username']
    cursor = conn.cursor();
    query = 'SELECT roleID From Act WHERE username = %s and roleID = 4'
    cursor.execute(query, (user))
    data = cursor.fetchone()
    if not data:
        flash("You have to be a donor to do the donation!")
        return redirect(url_for('home'))

    if request.method == 'POST':
        des = request.form['item_description']
        photo = request.form['photo']
        color = request.form['color']
        i = request.form['isnew']
        print(i)
        if i == "yes":
            isNew = 1
        else:
            isNew = 0
        h = request.form['haspiece']
        if h == "yes":
            hasPiece = 1
        else:
            hasPiece = 0
        material = request.form['material']
        main = request.form['main_category']
        sub = request.form['sub_category']
        catNote = request.form['cat_note']
        cursor.execute(
            "INSERT INTO Category (mainCategory, subCategory, catNotes) "
            "VALUES (%s, %s, %s)",
            ( main, sub, catNote),
        )
        cursor.execute(
            "INSERT INTO Item (iDescription,photo,color,isNew,hasPieces,material,mainCategory,subCategory,availability) "
            "VALUES (%s, %s, %s, %s, %s,%s,%s,%s,%s)",
            (des, photo, color, isNew,hasPiece,material,main,sub,1),
        )
        query3 = 'Select max(itemID) as max FROM item'
        cursor.execute(query3)
        itemID = cursor.fetchone()
        print(itemID)
        cursor.execute(
            "INSERT INTO donatedBy (ItemID,userName,donateDate,accepted) "
            "VALUES (%s, %s, %s, %s)",
            (itemID['max'],user,datetime.datetime.now(),0),
        )
        conn.commit()
        cursor.close()
        flash("You have successfully donated.")
        return redirect(url_for('home'))
    return render_template('donate.html')

@app.route('/applydonor', methods=['GET', 'POST'])
def applydonor():
    user = session['username']
    query = 'SELECT roleID From Act WHERE username = %s and roleID = 4'
    cursor = conn.cursor()
    cursor.execute(query, (user))
    data = cursor.fetchone()
    if data:
        flash("You are already a donor!")
        return redirect(url_for('home'))
    if request.method == 'POST':
        if request.form.get('ans') is None:
            flash("Please click Yes or No before you submit!")
            return render_template('applydonor.html')
        answer = request.form['ans']
        if answer == "no":
            return redirect(url_for('home'))

        cursor = conn.cursor();
        cursor.execute(
            "INSERT INTO Act (username, roleID) "
            "VALUES (%s, %s)",
            (user,4),
        )
        conn.commit()
        cursor.close()
        flash("You are a donor now!")
        return redirect(url_for('home'))
    return render_template('applydonor.html')

@app.route('/order', methods=['GET', 'POST'])
def order():
    user = session['username']
    query = 'SELECT roleID From Act WHERE username = %s and roleID = 1'
    cursor = conn.cursor()
    cursor.execute(query, (user))
    data = cursor.fetchone()
    if not data:
        flash("You have to be a staff to start an order!")
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        order_note = request.form['order_note']
        query2 = 'Select username From Person Where username = %s'
        cursor.execute(query2,(username))
        data2 = cursor.fetchone()
        if not data2:
            flash("This username does not exist!")
            return render_template('order.html')
        if data2['username'] == user:
            flash("You cannot start an order for yourself!")
            return render_template('order.html')
        query3 = 'SELECT max(orderID) as max FROM ordered'
        cursor.execute(query3)
        data3 = cursor.fetchone()
        orderID = data3['max'] +1
        cursor.execute(
            "INSERT INTO Ordered (orderID,orderDate, orderNotes,supervisor,client) "
            "VALUES (%s,%s, %s,%s,%s)",
            (orderID, datetime.datetime.now() ,order_note,user,username),
        )
        conn.commit()
        cursor.close()
        session['order'] = orderID
        flash("You have successfully created an order!")
        return redirect(url_for('home'))
    return render_template('order.html')

@app.route('/category', methods=['GET', 'POST'])
def category():
    query = 'SELECT distinct(mainCategory) From Item Natural Join donatedby WHERE availability = 1 and accepted = 1'
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()

    if not data:
        flash("There is nothing available now.")
        return redirect(url_for('home'))
    if request.method == 'POST':
        if request.form.get('category') is None:
            flash("You have to select a category to proceed!")
            return render_template('category.html', category=data)
        category = request.form['category']
        query2 = 'Select * From Item Natural Join Donatedby Where maincategory = %s and availability = 1 and accepted = 1'
        cursor.execute(query2,(category))
        data2 = cursor.fetchall()
        if not data2:
            flash("This category does not have anything now!")
            return redirect(url_for('category'))
        cursor.close()

        session['item'] = data2
        return redirect(url_for('shopping'))
    return render_template('category.html',category = data)

@app.route('/shopping', methods=['GET', 'POST'])
def shopping():
    orderID = session['order']
    item = session['item']
    cursor = conn.cursor()
    if not item:
        flash("There is nothing available now.")
        return redirect(url_for('home'))
    if request.method == 'POST':
        if request.form.get('target') is None:
            flash("You have to select an item to proceed!")
            return render_template('shopping.html', item=item)
        target = request.form['target']
        cursor.execute(
            "INSERT INTO Itemin (itemID, orderID,found) "
            "VALUES (%s,%s, %s)",
            (target,orderID, 0),
        )
        query2 = "Update Item set availability = 0 where itemID = %s"
        cursor.execute(query2, (target))
        conn.commit()
        cursor.close()
        flash("Item Successfully added to the order.")
        return redirect(url_for('home'))
    return render_template('shopping.html',item = item)

@app.route('/home')
def home():
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT roleID From Act WHERE username = %s'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    staff = False
    donor = False

    for roleID in data:

        if "1" == roleID['roleID']:
            staff = True
        if "4" == roleID['roleID']:
            donor = True
    cursor.close()
    return render_template('home.html', username=user, roles = data,staff = staff, donor = donor)


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
