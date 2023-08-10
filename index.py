from flask import Flask, request, flash, jsonify
import sqlite3
import json
import os
import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orenonawaerenjaeger'


conn = sqlite3.connect('./mains.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS authentication (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, username TEXT, img TEXT, likes INTEGER, caption TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, username TEXT, img TEXT, bio TEXT, followers INTEGER, following INTEGER, post_no INTEGER)''')
conn.commit()
conn.close()

@app.route('/home/<username>', methods=['GET'])  # Set the HTTP method to GET
def home(username):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()

    # Retrieve posts for the specified username
    c.execute('SELECT * FROM posts WHERE username = ?', (username,))
    posts = c.fetchall()

    conn.close()

    if posts:
        post_list = []
        for post in posts:
            post_dict = {
                'username': post[1],
                'img': post[2],
                'likes': post[3],
                'caption': post[4]
            }
            post_list.append(post_dict)
        
        return jsonify({'posts': post_list})
    else:
        return jsonify({'message': 'No posts found for this user'})
    
@app.route('/addPost/<username>', methods=['POST'])
def addPost(username):
    try:
        caption = request.form.get('caption')

        if caption is not None:
            conn = sqlite3.connect('./mains.db')
            c = conn.cursor()

            # Check if the username exists in the profiles table
            c.execute('SELECT * FROM profiles WHERE username = ?', (username,))
            existing_user = c.fetchone()

            if existing_user:
                # Save the image with a secure and unique name in the ./uploads directory
                upload_dir = './uploads'
                current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]  # Format timestamp
                filename = secure_filename(f"{current_timestamp}.jpg")
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                image_path = os.path.join(upload_dir, filename)
                image_data = request.files.get('image')  # Get the uploaded image data
                image_data.save(image_path)

                # Insert the new post with the image path
                c.execute('INSERT INTO posts (username, img, caption) VALUES (?, ?, ?)', (username, image_path, caption))
                conn.commit()
                conn.close()
                return jsonify({'message': 'Post added successfully', 'image_path': image_path})
            else:
                conn.close()
                return jsonify({'message': 'Username not found'}), 404
        else:
            return jsonify({'message': 'Caption is required'}), 409
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        try:
            data = json.loads(request.data)  # Parse JSON data
            username = data.get('username')
            password = data.get('password')

            if username is not None and password is not None:
                conn = sqlite3.connect('./mains.db')
                c = conn.cursor()

                # Check if username already exists
                c.execute('SELECT * FROM authentication WHERE username = ?', (username,))
                existing_user = c.fetchone()

                if existing_user is not None:
                    conn.close()
                    return 'Username already exists', 409  # Return 409 status code

                # Insert the new user
                c.execute('INSERT INTO authentication (username, password) VALUES (?, ?)', (username, password))
                conn.commit()
                conn.close()
                flash('Account created successfully...', 'success')
                return "Account created successfully"
            else:
                return "Invalid data received"
        except json.JSONDecodeError:
            return "Invalid JSON data received"


@app.route('/login', methods=['POST'])  # Fixed route definition and methods
def login():
    if request.method == 'POST':
        try:
            data = json.loads(request.data)
            username = data.get('username')
            password = data.get('password')

            if username is not None and password is not None:
                conn = sqlite3.connect('./mains.db')
                c = conn.cursor()
                c.execute('SELECT * FROM authentication WHERE username = ? AND password = ?', (username, password))
                user = c.fetchone()
                if user is None:
                    return 'Invalid username or password', 409
                conn.commit()
                conn.close()
                flash('Account Logged in successfully', 'success')
                return('Logged in successfully')
            else:
                return 'Invalid data received'
        except json.JSONDecodeError:
            return 'Invalid JSON data received'
        

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'No image part'})

        image = request.files['image']

        if image.filename == '':
            return jsonify({'message': 'No selected image'})

        if image:
            # Specify the directory where you want to save the image
            upload_dir = './uploads'
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # Save the image with a unique name
            image_path = os.path.join(upload_dir, image.filename)
            image.save(image_path)

            return jsonify({'message': 'Image uploaded successfully'})

    except Exception as e:
        return jsonify({'message': 'Error: {}'.format(str(e))})
    


imgs = 'https://blog.radware.com/wp-content/uploads/2020/06/anonymous.jpg'
@app.route('/addProfile', methods=['GET', 'POST'])
def addProfile():
    if request.method == 'POST':
        data = json.loads(request.data)
        username = data.get('username')
        bio = data.get('bio')
        img = imgs
        followers = 0
        following = 0
        post_no = 0
        conn = sqlite3.connect('./mains.db')
        c = conn.cursor()
        c.execute('INSERT INTO profiles (username, img, bio, followers, following, post_no) VALUES (?, ?, ?, ?, ?, ?)', (username, img, bio, followers, following, post_no))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Profile added successfully'})




if __name__ == '__main__':
    app.run(host='192.168.43.147', port=5000)
