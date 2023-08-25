from flask import Flask, request, flash, jsonify, send_from_directory
import sqlite3
import json
import os
import datetime
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'orenonawaerenjaeger'
cors = CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")



conn = sqlite3.connect('./mains.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS authentication (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, username TEXT, img TEXT, likes INTEGER, caption TEXT, height TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS profiles (id INTEGER PRIMARY KEY, username TEXT, img TEXT, bio TEXT, followers INTEGER, following INTEGER, post_no INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS followers_list (id INTEGER PRIMARY KEY, username TEXT, followers_ TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notification_follow (id INTEGER PRIMARY KEY, username TEXT, follower TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notification_unfollow (id INTEGER PRIMARY KEY, username TEXT, unfollower TEXT)''')
conn.commit()
conn.close()

def send_notification(username, message):
    emit('notification', {'username': username, 'message': message}, namespace='/notifications')

@socketio.on('connect', namespace='/notifications')
def connect():
    print('Client connected')

@app.route('/getNotifs/<username>', methods=['GET', 'POST'])
def get_notifs(username):
    try:
        conn = sqlite3.connect('./mains.db')
        c = conn.cursor()
        c.execute('SELECT * FROM notification_follow WHERE username = ?', (username, ))
        notifications = c.fetchall()
        conn.close()

        if notifications:
            notif_list = []
            for notif in notifications:
                notif_user_that_followed = notif[2].split(' ')
                userthatfollowed = notif_user_that_followed[0]
                print(userthatfollowed)
                notif_dict = {
                    'username': notif[1],
                    'follower': userthatfollowed,
                    'message': notif[2]
                }
                notif_list.append(notif_dict)
            
            return jsonify(notif_list)
        else:
            return jsonify({'message': 'No notifications found for the user'})
    
    except sqlite3.Error as e:
        return jsonify({'error': str(e)})

@app.route('/search/<query>', methods=['POST', 'GET'])
def search(query):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    query_with_wildcard = f'%{query}%'  # Add wildcards to the query

    c.execute('SELECT * FROM profiles WHERE username LIKE ?', (query_with_wildcard,))
    users = c.fetchall()
    conn.close()

    search_results = []

    if users:
        for user in users:
            user_dict = {
                'username': user[1],
                'bio': user[3],
                'img': user[2],
                'followers': user[4],
                'following': user[5],
                'post_no': user[6]
            }
            search_results.append(user_dict)

        return jsonify(search_results)
    else:
        return jsonify([])  # Return an empty list if no results found
    
@app.route('/checkFollow/<username>', methods=['POST'])
def check_follow(username):
    user_to_check = request.form.get('user2check')  # Use json data instead of form data
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    c.execute('SELECT followers_ FROM followers_list WHERE username = ?', (user_to_check,))
    followers_data = c.fetchone()
    conn.commit()
    conn.close()

    if followers_data:
        followers_string = followers_data[0]  # Extract the string from the tuple
        f_d = followers_string.split(',')
        print("Followers string:", followers_string)  # Print for debugging
        print("Followers list:", f_d)  # Print for debugging

        if username in f_d:
            return jsonify({
                'status': 'following',
                'no': len(f_d)
                })
        elif username not in f_d:
            return jsonify({
                'status': 'not_following',
                'no': len(f_d)
                })
        else:
            return jsonify({
                'status': 'Error',
                'no': 'No such one'
            })
    else:
        return jsonify({'status': 'user_not_found',})




@app.route('/addFollower/<username>', methods=['POST', 'GET'])
def addFollower(username):
    usertofollow = request.form.get('to_follow')
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    
    
    # Fetch the current followers list for the user
    c.execute('SELECT followers_ FROM followers_list WHERE username = ?', (usertofollow,))
    followers_data = c.fetchone()
    
    if followers_data is not None:
        print('Reached')
        current_followers = followers_data[0]
        if current_followers is None:
            current_followers = ''  # Set to an empty string if it's None

        if username not in current_followers:
            updated_followers = current_followers + ',' + username
            print('Reached3')
            c.execute('UPDATE followers_list SET followers_ = ? WHERE username = ?', (updated_followers, usertofollow))
            conn.commit()
            c.execute('INSERT INTO notification_follow (username, follower) VALUES (?, ?)', (usertofollow, f'{username} has followed you'))
            conn.commit()

            # Check if the username exists in the profiles table
            c.execute('SELECT followers FROM profiles WHERE username = ?', (usertofollow,))
            profile_data = c.fetchone()
            print(profile_data)
            print(len(profile_data))

            if profile_data is not None:
                # Update the followers count in the profiles table
                print(current_followers)
                updated_followers_count = len(current_followers) + 1
                cs = current_followers.split(',')
                css = len(cs) + 1
                print(len(cs))
                print(updated_followers_count)
                c.execute('UPDATE profiles SET followers = ? WHERE username = ?', (css, usertofollow))
                conn.commit()
                conn.close()
                return jsonify({'message': f'{username} is now following {usertofollow}'})
            else:
                conn.close()
                return jsonify({'message': 'User not found in profiles table'})
            
        elif followers_data is None:
            c.execute('INSERT INTO followers_list (username) VALUES (?)', (usertofollow, ))
            conn.commit()
            conn.close()
            return jsonify({ 'message': f'{usertofollow} has been added to followers list'})
        else:
            print('Reached2')
            conn.close()
            return jsonify({'message': f'{username} is already following {usertofollow}'})
        
    # Rest of your code...


    # Update the followers list in the database
        


    
    
@app.route('/unfollow/<username>', methods=['POST', 'GET'])
def unfollow(username):
    usertounfollow = request.form.get('to_unfollow')
    conn = sqlite3.connect('./mains.db')
    print(usertounfollow)
    c = conn.cursor()
    
    # Fetch the current followers list for the user
    c.execute('SELECT followers_ FROM followers_list WHERE username = ?', (username,))
    followers_data = c.fetchone()
    print(followers_data)
    

    if followers_data:
        f_d_l = len(followers_data)
        print(f_d_l)
        current_followers = followers_data[0].split(',')
        aa = len(current_followers)
        print(aa)
        if usertounfollow in current_followers:
            current_followers.remove(usertounfollow)
            updated_followers = ','.join(current_followers)
            print(username)

            # Update the followers list in the database
            c.execute('UPDATE followers_list SET followers_ = ? WHERE username = ?', (updated_followers, username))
            conn.commit()
            c.execute('UPDATE profiles SET followers = ? WHERE username = ?', (aa - 1, username))
            conn.commit()
            conn.close()
            return jsonify({'message': f'{username} unfollowed {usertounfollow}'})
        else:
            conn.close()
            return jsonify({'message': f'{username} is not following {usertounfollow}'})
    else:
        conn.close()
        return jsonify({'message': 'User not found'})


@app.route('/main/<username>', methods=['GET'])
def main(username):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()

    # Retrieve the followers list for the given username
    c.execute('SELECT followers_ FROM followers_list WHERE username = ?', (username,))
    followers_data = c.fetchone()

    if followers_data:
        followers_list = followers_data[0].split(',')
        followers_list = [follower.strip() for follower in followers_list]  # Trim whitespace
        print(followers_list)

        # Fetch posts for each follower
        post_list_s = []
        for follower in followers_list:
            c.execute('SELECT * FROM posts WHERE username = ?', (follower,))
            posts = c.fetchall()
            for post in posts:
                img_url = post[2].replace('\\', '/') if post[2] else None
                post_dict = {
                    'username': post[1],
                    'img': img_url,
                    'likes': post[3],
                    'caption': post[4],
                    'height': post[5]
                }
                post_list_s.append(post_dict)
        conn.commit()
        conn.close()
        return jsonify({'posts': post_list_s})
    else:
        conn.close()
        return jsonify({'message': 'No followers found for this user'})



@app.route('/home/<username>', methods=['GET'])  
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
            img_url = post[2].replace('\\', '/') if post[2] else None  # Replace backslashes with forward slashes
            post_dict = {
                'username': post[1],
                'img': img_url,
                'likes': post[3],
                'caption': post[4]
            }
            post_list.append(post_dict)
        
        return jsonify({'posts': post_list})
    else:
        return jsonify({'message': 'No posts found for this user'})
    
@app.route('/uploads/<path:filename>')
def serve_file(filename):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(os.path.join(root_dir, 'uploads'), filename)
    
@app.route('/addPost/<username>', methods=['POST'])
def addPost(username):
    try:
        caption = request.form.get('caption')
        height = request.form.get('height')
        likes = 0

        if caption is not None:
            conn = sqlite3.connect('./mains.db')
            c = conn.cursor()

            # Check if the username exists in the profiles table
            c.execute('SELECT * FROM profiles WHERE username = ?', (username,))
            existing_user = c.fetchone()

            if existing_user:
                # Save the image with a secure and unique name in the ./uploads directory
                upload_dir = 'uploads'
                current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]  # Format timestamp
                filename = secure_filename(f"{current_timestamp}.png")
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                image_path = os.path.join(upload_dir, filename)
                image_data = request.files.get('image')  # Get the uploaded image data
                image_data.save(image_path)

                # Insert the new post with the image path
                c.execute('INSERT INTO posts (username, img, likes, caption, height) VALUES (?, ?, ?, ?, ?)', (username, image_path, likes, caption, height))
                conn.commit()
                conn.close()
                
                # Correct the image URL by replacing backslashes with forward slashes
                image_url = f"http://192.168.43.147:5000/{image_path.replace(os.path.sep, '/')}"

                return jsonify({'message': 'Post added successfully', 'image_path': image_url})
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
                c.execute('INSERT INTO followers_list (username) VALUES (?)', username)
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
    
@app.route('/addLike/<username>', methods=['POST'])
def addLike(username):
    likes = int(request.form.get('likes')) + 1
    id = request.form.get('id')
    print(likes)
    print(id)
    
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    c.execute('UPDATE posts SET likes = ? WHERE username = ? AND caption = ?', (likes, username, id))
    conn.commit()
    conn.close()
    
    return jsonify({'message' : 'Like successfully updated'})



@app.route('/getProfile/<username>', methods=['GET'])
def getProfile(username):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    c.execute('SELECT * FROM profiles WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    
    if user is not None:
        # Assuming your profiles table has columns like 'username', 'full_name', 'bio', etc.
        profile_data = {
            'id': user[0],
            'username': user[1],
            'bio': user[3],
            'followers': user[4],
            'following': user[5],
            'post_no': user[6],
            'img': user[2]
            # Add more fields as needed
        }
        return jsonify(profile_data)
    else:
        return jsonify({'error': 'User not found'}), 404



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
