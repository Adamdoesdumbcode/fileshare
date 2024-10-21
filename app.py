import os
import time
import threading
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')

# Set the maximum file size limit to 128 MB
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024  # 128 MB limit

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dictionary to store server details, including creation time
servers = {}

def cleanup_servers():
    while True:
        time.sleep(60)  # Check every minute
        current_time = time.time()
        servers_to_delete = []
        
        for server_name, details in servers.items():
            # Check if the server has been up for more than 10 minutes (600 seconds)
            if current_time - details['created_at'] > 600:
                servers_to_delete.append(server_name)

        for server_name in servers_to_delete:
            del servers[server_name]
            # Optionally, delete all files in the uploads folder for this server
            for filename in os.listdir(UPLOAD_FOLDER):
                if filename.startswith(server_name + '_'):
                    os.remove(os.path.join(UPLOAD_FOLDER, filename))

# Start the cleanup thread
threading.Thread(target=cleanup_servers, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create_server():
    if request.method == 'POST':
        server_name = request.form['server_name']
        password = request.form['password']
        
        if server_name not in servers:
            # Store creation time
            servers[server_name] = {
                'password': password,
                'files': [],
                'created_at': time.time()  # Store the current time
            }
            session['server_name'] = server_name
            return redirect(url_for('upload'))
        else:
            return "Server already exists!", 400

    return render_template('create.html')

@app.route('/join', methods=['GET', 'POST'])
def join_server():
    if request.method == 'POST':
        server_name = request.form['server_name']
        password = request.form['password']

        if server_name in servers and servers[server_name]['password'] == password:
            session['server_name'] = server_name
            return redirect(url_for('upload'))
        else:
            return "Invalid server name or password!", 400

    return render_template('join.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'server_name' not in session:
        return redirect(url_for('index'))

    server_name = session['server_name']

    if request.method == 'POST':
        file = request.files['file']
        if file:
            try:
                # Prefix files with server name to avoid collisions
                file_path = os.path.join(UPLOAD_FOLDER, f"{server_name}_{file.filename}")
                file.save(file_path)
                servers[server_name]['files'].append(file.filename)
                return redirect(url_for('upload'))
            except Exception as e:
                return f"An error occurred while saving the file: {e}", 500

    return render_template('upload.html', files=servers[server_name]['files'], server_name=server_name)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/logout')
def logout():
    session.pop('server_name', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
