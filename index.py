from flask import Flask, request, flash, jsonify, send_from_directory, make_response
import sqlite3
import json
import os
import datetime
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime

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
c.execute('''CREATE TABLE IF NOT EXISTS following_list (id INTEGER PRIMARY KEY, username TEXT, following TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS post_likers (id INTEGER PRIMARY KEY, post_id INTEGER, post_likers TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, sender TEXT, receiver TEXT, message TEXT, timestamp TEXT)''')
conn.commit()
conn.close()

@app.route('/getUsersFollowing/<username>', methods=['GET'])
def getUsersFollowing(username):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()

    # Get the list of users that 'username' is following
    c.execute('SELECT following FROM following_list WHERE username = ?', (username,))
    users = c.fetchone()
    
    if users is not None:
        following_list = users[0].split(',')  # Split the comma-separated list of usernames
        mutual_followers = []  # Initialize a list to store mutual followers

        # Check each user in the following_list
        for following_username in following_list:
            # Query the followers_list table to check if it's a mutual follower
            c.execute('SELECT * FROM followers_list WHERE username = ? AND follower_username = ?', (following_username, username))
            result = c.fetchone()
            
            if result is not None:
                # If it's a mutual follower, add them to the list
                mutual_followers.append(following_username)

        conn.close()
        return jsonify(mutual_followers)
    else:
        conn.close()
        return jsonify({'error': 'User not found'}), 404



def send_notification(username, message):
    emit('notification', {'username': username, 'message': message}, namespace='/notifications')

@socketio.on('new_chatter')
def new_chatter(data):
    #Tomiwa finish this route
    return

@socketio.on('send_message')
def send_message(data):
    try:
        message = data.get('message')
        sender = data.get('sender')
        receiver = data.get('receiver')

        if message and sender and receiver:
            conn = sqlite3.connect('./mains.db')
            c = conn.cursor()

            # Get the current timestamp in the format 'HH:MM:SS'
            timestamp = datetime.now().strftime('%H:%M')

            c.execute('INSERT INTO messages (sender, receiver, message, timestamp) VALUES (?, ?, ?, ?)',
                      (sender, receiver, message, timestamp))
            conn.commit()
            conn.close()

            socketio.emit('send_message', {'sender': sender, 'receiver': receiver, 'message': message, 'timestamp': timestamp})
            # Emit a success message to the client if needed.
            socketio.emit('message_success', {'message': 'Message sent successfully'})
            socketio.emit('new_message', {'sender': sender, 'receiver': receiver, 'message_content': message, 'timestamp': timestamp})
        else:
            # Emit a failure message to the client if data is missing.
            socketio.emit('message_failure', {'message': 'Incomplete message data'})

    except Exception as e:
        # Handle any exceptions that may occur during database insertion.
        # You can log the error or emit an error message to the client.
        print(f"Error: {str(e)}")
        socketio.emit('message_failure', {'message': 'An error occurred while sending the message'})


@socketio.on('new_message')
def new_message(data):
    sender = data['sender']
    receiver = data['receiver']
    message_content = data['message_content']

    socketio.emit('new_message', {'sender': sender, 'receiver': receiver, 'message_content': message_content})


@app.route('/retrieveMessage/<username>/<chatWith>', methods=['GET'])
def retrieveMessage(username, chatWith):
    try:
        conn = sqlite3.connect('./mains.db')
        c = conn.cursor()
        c.execute('SELECT * FROM messages WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)',
                  (username, chatWith, chatWith, username))
        messages = c.fetchall()
        conn.close()

        message_list = []

        if messages:
            for message in messages:
                m_list = {
                    'Id': message[0],
                    'sender': message[1],
                    'receiver': message[2],
                    'message': message[3],
                    'timestamp': message[4],
                    'hasNewMessage': False  # Initialize hasNewMessage as False by default
                }
                message_list.append(m_list)

        return jsonify(message_list)

    except sqlite3.Error as e:
        # Handle database connection or query errors.
        print(f"Database error: {str(e)}")
        return jsonify({'error': 'An error occurred while retrieving messages'})

    except Exception as e:
        # Handle other exceptions.
        print(f"Error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'})



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
    

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('custom_message')
def handle_custom_message(data):
    message = data['message']
    sender = data['sender']
    # Process the message data as needed
    print(f'Received message from {sender}: {message}')
    # Broadcast the message to all connected clients
    socketio.emit('custom_message', {'sender': sender, 'message': message})

@socketio.on('liked_post')
def liked_post(data):
    print('Liked Post')
    id = data['id']
    print(id)
    like_no = data['like_no']
    username = data['username']
    print(username)
    print(like_no)
    
    # Update the like count in the database
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    new_likes = int(like_no) + 1
    print(new_likes)

    print('OK')
    c.execute('SELECT * FROM post_likers WHERE post_id = ?', (id,))
    print('1')
    cs = c.fetchall()
    if cs is not None:
        c.execute('SELECT post_likers FROM post_likers WHERE post_id = ?', (id,))
        print('2')
        css = c.fetchone()
        if css is not None:
            cap = css[0]
            if cap is None:
                cap = ''
            if username not in cap:
                if not cap:
                    updated_likers = username  # Set to username directly
                else:
                    updated_likers = cap + ',' + username

                print(f'Updated Likers: {updated_likers}')
                c.execute('UPDATE post_likers SET post_likers = ? WHERE post_id = ?', (updated_likers, id))
                conn.commit()
                c.execute('UPDATE posts SET likes = ? WHERE id = ?', (new_likes, id))
                socketio.emit('liked_post', {'id': id, 'likes': new_likes, 'username': username})
                print('Done')
                conn.commit()
                conn.close()
            else:
                unliked_post(data)

        else:
            c.execute('INSERT INTO post_likers (post_id, post_likers) VALUES (?, ?)', (id, username))
            socketio.emit('liked_post', {'id': id, 'likes': new_likes, 'username': username})
            conn.commit()
            c.execute('UPDATE posts SET likes = ? WHERE id = ?', (new_likes, id))
            conn.commit()
            conn.close()
        # Emit a Socket.IO event to notify clients about the change
    

@socketio.on('unliked_post')
def unliked_post(data):
    id = data['id']
    username = data['username']
    like_no = data['like_no']
    print(f'Id, Uid, like_no {id}, {username}, {like_no}')

    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    new_likes = int(like_no) - 1

    c.execute('SELECT * FROM post_likers WHERE post_id = ?', (id,))
    css = c.fetchall()
    if css is not None:
        c.execute('SELECT post_likers FROM post_likers WHERE post_id = ?', (id,))
        csss = c.fetchone()
        if csss is not None:
            pac = csss[0]
            pacs = pac.split(',')
            print('Pac:', pacs)
            if not pacs:
                pacs = []
            if username in pacs:
                pacs.remove(username)
                upd_likers = ','.join(pacs)
                c.execute('UPDATE post_likers SET post_likers = ? WHERE post_id = ?', (upd_likers, id))
                conn.commit()
                c.execute('UPDATE posts SET likes = ? WHERE id = ?', (new_likes, id))
                conn.commit()
            else:
                return
        else:
            return
    else:
        return jsonify({'message': 'No such post'})
    
    socketio.emit('unliked_post', {'id': id, 'likes': new_likes, 'username': username})




@app.route('/addFollower/<username>', methods=['POST', 'GET'])
def addFollower(username):
    usertofollow = request.form.get('to_follow')
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()

    # Fetch the current followers list for the user
    c.execute('SELECT followers_ FROM followers_list WHERE username = ?', (usertofollow, ))
    followers_data = c.fetchone()

    if followers_data is not None:
        print('Reached')
        current_followers = followers_data[0]
        if current_followers is None:
            current_followers = ''  # Set to an empty string if it's None

        if username not in current_followers:
            updated_followers = current_followers + ',' + username
            print(f'Updated followers: {updated_followers}')
            print('Reached3')
            c.execute('UPDATE followers_list SET followers_ = ? WHERE username = ?', (updated_followers, usertofollow))
            conn.commit()
            c.execute('SELECT following FROM following_list WHERE username = ?', (username,))
            ss = c.fetchone()
            if ss is not None:
                current_following = ss[0].split(',')
                if usertofollow not in current_following:
                    current_following.append(usertofollow)  # Add your username to the list
                    updated_following = ','.join(current_following)
                    c.execute('UPDATE following_list SET following = ? WHERE username = ?', (updated_following, username))
                    conn.commit()

                    print('I did')
                    c.execute('INSERT INTO notification_follow (username, follower) VALUES (?, ?)', (usertofollow, f'{username} has followed you'))
                    conn.commit()
                    followers_count = len(current_followers)+1
                    c.execute('INSERT INTO profiles (followers) VALUES (?)', (followers_count, ))
                    conn.commit()
                    
                elif username in current_following:
                    return jsonify({'message':f'{username} already follows {usertofollow}'})
                else:
                    return jsonify({'message':'Error in following'})
            else:
                c.execute('INSERT INTO following_list (username, following) VALUES (?, ?)', (usertofollow, username))
                conn.commit()
                c.execute('INSERT INTO notification_follow (username, follower) VALUES (?, ?)', (usertofollow, f'{username} has followed you'))
                conn.commit()

        # Check if the username exists in the profiles table
        c.execute('SELECT followers FROM profiles WHERE username = ?', (usertofollow,))
        print('It reached here')
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
        current_followers = ''
        updated_followers = current_followers + username
        print(updated_followers)
        c.execute('INSERT INTO followers_list (username, followers_) VALUES (?, ?)', (usertofollow, updated_followers))
        conn.commit()
        c.execute('UPDATE profiles SET followers = ? WHERE username = ?', (len(updated_followers), username))
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
            c.execute('SELECT following FROM following_list WHERE username = ?', (usertounfollow,))
            sss = c.fetchone()
            if sss is not None:
                current_following = sss[0].split(',')
                if username in current_following:
                    current_following.remove(username)
                    updated_following = ','.join(current_following)
                    print(updated_following)
                    c.execute('UPDATE following_list SET following = ? WHERE username = ?', (updated_following, usertounfollow))
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


@app.route('/getPosts/<username>', methods=['GET'])
def getPosts(username):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()

    c.execute('SELECT following FROM following_list WHERE username = ?', (username,))
    following_data = c.fetchone()

    if following_data:
        following_list = following_data[0].split(',')
        following_list = [following.strip() for following in following_list]
        print(following_list)

        post_list = []  # To store the posts

        # Determine the maximum ID
        c.execute('SELECT MAX(id) FROM posts')
        max_id = c.fetchone()[0]

        if max_id is not None:
            # Calculate the starting ID for fetching the latest 10 posts
            start_id = max(max_id - 10, 1)  # Ensure start_id is at least 1

            for following in following_list:
                # Fetch the latest 10 posts from each following user
                c.execute('SELECT * FROM posts WHERE username = ? AND id >= ? ORDER BY id DESC LIMIT 8', (following, start_id))
                posts = c.fetchall()

                # Iterate through the fetched posts and check if they have been liked by the user
                for post in posts:
                    img_url = post[2].replace('\\', '/') if post[2] else None

                    # Check if the user has already liked the post
                    c.execute('SELECT post_likers FROM post_likers WHERE post_id = ?', (post[0],))
                    likers_data = c.fetchone()
                    likers_string = likers_data[0] if likers_data else ''

                    # Split the likers string into a list of usernames
                    likers_list = likers_string.split(',')

                    # Check if the username is in the list of likers
                    already_liked = username in likers_list

                    post_dict = {
                        'username': post[1],
                        'caption': post[4],
                        'likes': post[3],
                        'height': post[5],
                        'id': post[0],
                        'img': img_url,
                        'alreadyLiked': already_liked  # Add a flag to indicate if the post has already been liked
                    }
                    post_list.append(post_dict)

        return jsonify(post_list)

    return jsonify([])  # Return an empty list if no following data found

@app.route('/fetchPosts/<username>', methods=['GET'])
def fetchPosts(username):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()
    c.execute('SELECT following FROM following_list WHERE username = ?', (username,))
    following_data = c.fetchone()

    if following_data is not None:
        following_list = following_data[0].split(',')
        following_list = [following.strip() for following in following_list]
        following_list.append(username)
        print(following_list)

        post_list = []  # To store the posts

        # Determine the maximum ID
        c.execute('SELECT MAX(id) FROM posts')
        max_id = c.fetchone()[0]

        if max_id is not None:
            # Calculate the starting ID for fetching the latest 10 posts
            start_id = max(max_id - 10, 1)  # Ensure start_id is at least 1

            for following in following_list:
                # Fetch the latest 10 posts from each following user
                c.execute('SELECT * FROM posts WHERE username = ? AND id >= ? ORDER BY id DESC LIMIT 8', (following, start_id))
                posts = c.fetchall()

                for post in posts:
                    img_url = post[2].replace('\\', '/') if post[2] else None
                    c.execute('SELECT post_likers FROM post_likers WHERE post_id = ?', (post[0],))
                    likers_data = c.fetchone()
                    likers_string = likers_data[0] if likers_data else ''

                    # Split the likers string into a list of usernames
                    likers_list = likers_string.split(',')

                    # Check if the username is in the list of likers
                    already_liked = username in likers_list
                    isVideo = img_url.endswith('.mp4')
                    post_dict = {
                        'username': post[1],
                        'caption': post[4],
                        'likes': post[3],
                        'height': post[5],
                        'id': post[0],
                        'img': img_url,
                        'alreadyLiked': already_liked,  # Add a flag to indicate if the post has already been liked
                        'isVideo': isVideo
                    }
                    post_list.append(post_dict)

        return jsonify(post_list)

    return jsonify([])  # Return an empty list if no following data found


@app.route('/getMorePosts/<username>/<lastPostId>', methods=['GET', 'POST'])
def getMorePosts(username, lastPostId):
    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()


    if lastPostId is None:
        # Handle the case where no last post ID is provided
        return jsonify(message='Last post ID is required'), 400
    
    c.execute('SELECT following FROM following_list WHERE username = ?', (username,))
    following_data = c.fetchone()

    if following_data:
        following_list = following_data[0].split(',')
        following_list = [following.strip() for following in following_list]
        print(following_list)

        post_list = []

        for following_username in following_list:
            # Fetch posts for each following username
            c.execute('SELECT * FROM posts WHERE username = ? AND id <= ? ORDER BY id ASC LIMIT 10', (following_username, lastPostId))
            more_posts = c.fetchall()

            for post in more_posts:
                img_url = post[2].replace('\\', '/') if post[2] else None
                post_dict = {
                    'username': post[1],
                    'caption': post[4],
                    'likes': post[3],
                    'height': post[5],
                    'id': post[0],
                    'img': img_url
                }
                post_list.append(post_dict)

        conn.close()
        return jsonify(post_list)
    
    conn.close()
    return jsonify([])  # Return an empty list if no following data found







@app.route('/main/<username>', methods=['GET'])
def main(username):
    # Parse query parameters for pagination
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)

    conn = sqlite3.connect('./mains.db')
    c = conn.cursor()

    # Retrieve the followers list for the given username
    c.execute('SELECT following FROM following_list WHERE username = ?', (username,))
    following_data = c.fetchone()

    if following_data:
        following_list = following_data[0].split(',')
        following_list = [following.strip() for following in following_list]  # Trim whitespace
        print(following_list)

        # Fetch posts for each follower with pagination
        post_list_s = []
        for following in following_list:
            c.execute('SELECT * FROM posts WHERE username = ? LIMIT ? OFFSET ?',
                      (following, per_page, (page - 3) * per_page))
            posts = c.fetchall()
            for post in posts:
                img_url = post[2].replace('\\', '/') if post[2] else None
                post_dict = {
                    'username': post[1],
                    'img': img_url,
                    'likes': post[3],
                    'caption': post[4],
                    'height': post[5],
                    'id': post[0]
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
def serve_video(filename):
    video_path = 'uploads'  # Replace with the actual path to your video files directory
    full_path = os.path.join(video_path, filename)

    # Check if the file exists
    if not os.path.isfile(full_path):
        return "Video not found", 404

    # Determine the content type based on the file extension
    if filename.endswith('.mp4'):
        content_type = 'video/mp4'
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(os.path.join(root_dir, 'uploads'), filename)

    # Set the Content-Disposition header to display the file inline
    response = make_response(send_from_directory(video_path, filename, mimetype=content_type))
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'

    return response
    
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

                return jsonify({'message': 'Post added successfully', 'image_path': image_url}), 200
            else:
                conn.close()
                return jsonify({'message': 'Username not found'}), 404
        else:
            return jsonify({'message': 'Caption is required'}), 409
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
    
@app.route('/addVideo/<username>', methods=['POST'])
def addVideo(username):
    try:
        caption = request.form.get('caption')
        height = request.form.get('height')
        likes = 0

        if caption is not None:
            conn = sqlite3.connect('./mains.db')
            c = conn.cursor()
            c.execute('SELECT * FROM profiles WHERE username = ?', (username,))
            existing_user = c.fetchone()

            if existing_user:
                upload_dir = 'uploads'
                current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]  # Format timestamp
                filename = secure_filename(f"{current_timestamp}.mp4")
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                vid_path = os.path.join(upload_dir, filename)
                vid_data = request.files.get('video')
                if vid_data is None:
                    print("No video file found in the request.")
                else:
                    print(f"Received video file: {vid_data.filename}")
                    vid_data.save(vid_path)


                c.execute('INSERT INTO posts (username, img, likes, caption, height) VALUES(?, ?, ?, ?, ?)', (username, vid_path, likes, caption, height))
                conn.commit()
                conn.close()

                vid_url = f"http://192.168.43.228:5000/{vid_path.replace(os.path.sep, '/')}"

                return jsonify({'message': 'Video Upload Successful', 'vid_path':vid_url, 'status': 200}), 200
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
                c.execute('INSERT INTO followers_list (username) VALUES (?)', (username,))
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
        c.execute('INSERT INTO following_list (username) VALUES (?)', (username,))
        conn.commit()
        c.execute('INSERT INTO notification_follow (username) VALUES (?)', (username,))
        conn.commit()
        c.execute('INSERT INTO notification_unfollow (username) VALUES (?)', (username,))
        conn.commit()
        c.execute('INSERT INTO followers_list (username) VALUES (?)', (username,))
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
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
