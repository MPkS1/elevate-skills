from flask import Flask, render_template, request, session, redirect, url_for, flash
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random key

# Connect to Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user details from Supabase
        user_data = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()

        if user_data.data:
            user = user_data.data[0]
            session['username'] = user['username']
            session['role'] = user['role']

            # Redirect based on role
            role_routes = {
                'special_admin': 'special_admin',
                'admin': 'admin',
                'winghead': 'winghead_dashboard',
                'member': 'member_dashboard'
            }
            return redirect(url_for(role_routes[user['role']]))
        
        flash('Invalid username or password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/special_admin', methods=['GET', 'POST'])
def special_admin():
    if 'username' not in session or session['role'] != 'special_admin':
        return redirect(url_for('login'))

    user_data = supabase.table('users').select('*').eq('username', session['username']).execute().data[0]

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create_wing':
            wing_name = request.form['wing_name']
            supabase.table('wings').insert({"name": wing_name}).execute()
            flash('Wing Created Successfully!', 'success')

        elif action == 'delete_wing':
            wing_id = request.form['wing_id']
            supabase.table('wings').delete().eq('id', wing_id).execute()
            flash('Wing Deleted!', 'danger')

        elif action == 'create_user':
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            wing_id = request.form['wing_id'] if role != 'special_admin' else None  
            existing_user = supabase.table('users').select('*').eq('username', username).execute()
            if existing_user.data:
                flash('Username already exists!', 'danger')
            else:
                supabase.table('users').insert({
                    "username": username,
                    "password": password,
                    "role": role,
                    "wing_id": wing_id
                }).execute()
                flash('User Created!', 'success')

        elif action == 'delete_user':
            user_id = request.form['user_id']
            supabase.table('users').delete().eq('id', user_id).execute()
            flash('User Deleted!', 'danger')

        elif action == 'delete_learning':
            learning_id = request.form['learning_id']
            supabase.table('learnings').delete().eq('id', learning_id).execute()
            flash('Learning response deleted!', 'danger')

        elif action == 'create_quiz':
            question = request.form['question']
            quiz_type = request.form['quiz_type']
            wing_id = request.form['wing_id'] or None
            options = [request.form.get(f'option_{i}') for i in range(1, (int(quiz_type[0]) if quiz_type != 'text' else 1) + 1)] if quiz_type != 'text' else None
            correct_option = int(request.form['correct_option']) - 1 if quiz_type != 'text' else None

            quiz_response = supabase.table('quizzes').insert({
                "question": question,
                "quiz_type": quiz_type,
                "wing_id": wing_id,
                "creator_id": user_data['id']
            }).execute()
            quiz_id = quiz_response.data[0]['id']

            if quiz_type != 'text':
                for i, option_text in enumerate(options):
                    supabase.table('quiz_options').insert({
                        "quiz_id": quiz_id,
                        "option_text": option_text,
                        "is_correct": i == correct_option
                    }).execute()
            flash("Quiz created!", "success")

        elif action == 'delete_quiz':
            quiz_id = request.form['quiz_id']
            supabase.table('quizzes').delete().eq('id', quiz_id).execute()
            flash("Quiz deleted!", "danger")

        elif action == 'send_notification':
            content = request.form['notification_content']
            wing_id = request.form['wing_id'] or None
            supabase.table('notifications').insert({
                "content": content,
                "wing_id": wing_id,
                "sender_id": user_data['id']
            }).execute()
            flash("Notification sent!", "success")

        elif action == 'send_news':
            content = request.form['news_content']
            supabase.table('news').insert({
                "content": content,
                "sender_id": user_data['id']
            }).execute()
            flash("News sent!", "success")

        elif action == 'delete_notification':
            notification_id = request.form['notification_id']
            supabase.table('notifications').delete().eq('id', notification_id).execute()
            flash("Notification deleted!", "danger")

        elif action == 'delete_news':
            news_id = request.form['news_id']
            supabase.table('news').delete().eq('id', news_id).execute()
            flash("News deleted!", "danger")

    wings = supabase.table('wings').select('*').execute().data or []
    users = supabase.table('users').select('*').execute().data or []

    members_count = len([u for u in users if u['role'] == 'member'])
    wingheads_count = len([u for u in users if u['role'] == 'winghead'])
    admins_count = len([u for u in users if u['role'] == 'admin'])
    special_admins_count = len([u for u in users if u['role'] == 'special_admin'])

    selected_wing_id = request.form.get('wing_id') if request.method == 'POST' else None
    learnings = []
    if selected_wing_id:
        learnings = supabase.table('learnings').select('id, username, role, learning_text').eq('wing_id', selected_wing_id).execute().data or []

    quizzes = supabase.table('quizzes').select('id, question, quiz_type, wing_id').execute().data or []
    selected_quiz_id = request.args.get('quiz_id')
    responses = []
    if selected_quiz_id:
        responses = supabase.table('quiz_responses').select('user_id, selected_option_id, text_response').eq('quiz_id', selected_quiz_id).execute().data or []
        for r in responses:
            r['username'] = supabase.table('users').select('username').eq('id', r['user_id']).execute().data[0]['username']
            r['wing_id'] = supabase.table('users').select('wing_id').eq('id', r['user_id']).execute().data[0]['wing_id']
            if r['wing_id']:
                r['wing_name'] = supabase.table('wings').select('name').eq('id', r['wing_id']).execute().data[0]['name']
            if r['selected_option_id']:
                option = supabase.table('quiz_options').select('option_text, is_correct').eq('id', r['selected_option_id']).execute().data[0]
                r['option_text'] = option['option_text']
                r['is_correct'] = option['is_correct']

    notifications = supabase.table('notifications').select('id, content, sent_at, wing_id').order('sent_at', desc=True).limit(5).execute().data or []
    news = supabase.table('news').select('id, content, sent_at').order('sent_at', desc=True).limit(5).execute().data or []

    return render_template('special_admin_dashboard.html', wings=wings, users=users,
                          members_count=members_count, wingheads_count=wingheads_count,
                          admins_count=admins_count, special_admins_count=special_admins_count,
                          learnings=learnings, selected_wing_id=selected_wing_id,
                          quizzes=quizzes, responses=responses, selected_quiz_id=selected_quiz_id,
                          notifications=notifications, news=news)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    user_data = supabase.table('users').select('*').eq('username', session['username']).execute().data[0]

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create_wing':
            wing_name = request.form['wing_name']
            supabase.table('wings').insert({"name": wing_name}).execute()
            flash('Wing Created!', 'success')

        elif action == 'create_user':
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            wing_id = request.form['wing_id']
            existing_user = supabase.table('users').select('*').eq('username', username).execute()
            if existing_user.data:
                flash('Username already exists!', 'danger')
            else:
                supabase.table('users').insert({
                    "username": username,
                    "password": password,
                    "role": role,
                    "wing_id": wing_id
                }).execute()
                flash('User Created!', 'success')

        elif action == 'create_quiz':
            question = request.form['question']
            quiz_type = request.form['quiz_type']
            wing_id = request.form['wing_id'] or None
            options = [request.form.get(f'option_{i}') for i in range(1, (int(quiz_type[0]) if quiz_type != 'text' else 1) + 1)] if quiz_type != 'text' else None
            correct_option = int(request.form['correct_option']) - 1 if quiz_type != 'text' else None

            quiz_response = supabase.table('quizzes').insert({
                "question": question,
                "quiz_type": quiz_type,
                "wing_id": wing_id,
                "creator_id": user_data['id']
            }).execute()
            quiz_id = quiz_response.data[0]['id']

            if quiz_type != 'text':
                for i, option_text in enumerate(options):
                    supabase.table('quiz_options').insert({
                        "quiz_id": quiz_id,
                        "option_text": option_text,
                        "is_correct": i == correct_option
                    }).execute()
            flash("Quiz created!", "success")

        elif action == 'send_notification':
            content = request.form['notification_content']
            wing_id = request.form['wing_id'] or None
            supabase.table('notifications').insert({
                "content": content,
                "wing_id": wing_id,
                "sender_id": user_data['id']
            }).execute()
            flash("Notification sent!", "success")

        elif action == 'send_news':
            content = request.form['news_content']
            supabase.table('news').insert({
                "content": content,
                "sender_id": user_data['id']
            }).execute()
            flash("News sent!", "success")

    wings = supabase.table('wings').select('*').execute().data or []
    members = supabase.table('users').select('*').eq('role', 'member').execute().data or []
    wingheads = supabase.table('users').select('*').eq('role', 'winghead').execute().data or []
    admins = supabase.table('users').select('*').eq('role', 'admin').execute().data or []
    special_admins = supabase.table('users').select('*').eq('role', 'special_admin').execute().data or []

    members_count = len(members)
    wingheads_count = len(wingheads)
    admins_count = len(admins)
    special_admins_count = len(special_admins)

    selected_wing_id = request.form.get('wing_id') if request.method == 'POST' else None
    learnings = []
    if selected_wing_id:
        learnings = supabase.table('learnings').select('username, role, learning_text').eq('wing_id', selected_wing_id).execute().data or []

    quizzes = supabase.table('quizzes').select('id, question, quiz_type, wing_id').eq('creator_id', user_data['id']).execute().data or []
    selected_quiz_id = request.args.get('quiz_id')
    responses = []
    if selected_quiz_id:
        responses = supabase.table('quiz_responses').select('user_id, selected_option_id, text_response').eq('quiz_id', selected_quiz_id).execute().data or []
        for r in responses:
            r['username'] = supabase.table('users').select('username').eq('id', r['user_id']).execute().data[0]['username']
            r['wing_id'] = supabase.table('users').select('wing_id').eq('id', r['user_id']).execute().data[0]['wing_id']
            if r['wing_id']:
                r['wing_name'] = supabase.table('wings').select('name').eq('id', r['wing_id']).execute().data[0]['name']
            if r['selected_option_id']:
                option = supabase.table('quiz_options').select('option_text, is_correct').eq('id', r['selected_option_id']).execute().data[0]
                r['option_text'] = option['option_text']
                r['is_correct'] = option['is_correct']

    notifications = supabase.table('notifications').select('id, content, sent_at, wing_id').eq('sender_id', user_data['id']).order('sent_at', desc=True).limit(5).execute().data or []
    news = supabase.table('news').select('id, content, sent_at').eq('sender_id', user_data['id']).order('sent_at', desc=True).limit(5).execute().data or []

    return render_template('admin_dashboard.html', wings=wings, members=members, wingheads=wingheads, 
                          admins=admins, special_admins=special_admins, members_count=members_count, 
                          wingheads_count=wingheads_count, admins_count=admins_count, 
                          special_admins_count=special_admins_count, learnings=learnings, 
                          selected_wing_id=selected_wing_id, quizzes=quizzes, responses=responses, 
                          selected_quiz_id=selected_quiz_id, notifications=notifications, news=news)

@app.route('/create_user', methods=['POST'])
def create_user():
    if 'role' not in session or session['role'] not in ['admin', 'special_admin']:
        return redirect(url_for('login'))

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    wing_id = request.form['wing_id']

    if session['role'] == 'admin' and role == 'special_admin':
        flash("Admins cannot create special admins!", "danger")
        return redirect(url_for('admin'))

    existing_user = supabase.table('users').select('*').eq('username', username).execute()
    if existing_user.data:
        flash("Username already exists!", "danger")
    else:
        response = supabase.table('users').insert({
            'username': username,
            'password': password,
            'role': role,
            'wing_id': wing_id
        }).execute()
        if response.error:
            flash(f"Error creating user: {response.error}", "danger")
        else:
            flash("User created successfully!", "success")

    return redirect(url_for('special_admin' if session['role'] == 'special_admin' else 'admin'))

@app.route('/member_dashboard', methods=['GET', 'POST'])
def member_dashboard():
    if 'username' not in session or session['role'] != 'member':
        return redirect(url_for('login'))

    username = session['username']
    user_data = supabase.table('users').select('*').eq('username', username).execute().data[0]
    wing_id = user_data['wing_id']

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'submit_quiz':
            quiz_id = request.form['quiz_id']
            selected_option_id = request.form.get('option_id')
            text_response = request.form.get('text_response')

            existing_response = supabase.table('quiz_responses').select('*').eq('quiz_id', quiz_id).eq('user_id', user_data['id']).execute()
            if not existing_response.data:
                supabase.table('quiz_responses').insert({
                    "quiz_id": quiz_id,
                    "user_id": user_data['id'],
                    "selected_option_id": selected_option_id if selected_option_id else None,
                    "text_response": text_response if text_response else None
                }).execute()
                flash("Quiz submitted!", "success")

        elif action == 'submit_learning':
            learning_text = request.form['learning_text']
            supabase.table('learnings').insert({
                "username": username,
                "wing_id": wing_id,
                "role": "member",
                "learning_text": learning_text
            }).execute()
            flash("Learning updated!", "success")

    learnings = supabase.table('learnings').select('learning_text').eq('wing_id', wing_id).execute().data or []
    quizzes = supabase.table('quizzes').select('id, question, quiz_type').eq('wing_id', wing_id).execute().data or []
    all_wing_quizzes = supabase.table('quizzes').select('id, question, quiz_type').is_('wing_id', 'null').execute().data or []
    quizzes.extend(all_wing_quizzes)

    quiz_data = []
    for quiz in quizzes:
        options = supabase.table('quiz_options').select('id, option_text, is_correct').eq('quiz_id', quiz['id']).execute().data or []
        response = supabase.table('quiz_responses').select('selected_option_id, text_response').eq('quiz_id', quiz['id']).eq('user_id', user_data['id']).execute().data
        quiz_data.append({
            'quiz': quiz,
            'options': options,
            'response': response[0] if response else None
        })

    # Fetch notifications (wing-specific and all-wing)
    wing_notifications = supabase.table('notifications').select('content, sent_at').eq('wing_id', wing_id).order('sent_at', desc=True).limit(5).execute().data or []
    all_notifications = supabase.table('notifications').select('content, sent_at').is_('wing_id', 'null').order('sent_at', desc=True).limit(5).execute().data or []
    notifications = wing_notifications + all_notifications
    notifications.sort(key=lambda x: x['sent_at'], reverse=True)
    notifications = notifications[:5]  # Limit to latest 5

    news = supabase.table('news').select('content, sent_at').order('sent_at', desc=True).limit(5).execute().data or []

    return render_template('member_dashboard.html', learnings=learnings, username=username, quiz_data=quiz_data, 
                          notifications=notifications, news=news)


@app.route('/winghead_dashboard', methods=['GET', 'POST'])
def winghead_dashboard():
    if 'username' not in session or session['role'] != 'winghead':
        return redirect(url_for('login'))

    username = session['username']
    user_data = supabase.table('users').select('*').eq('username', username).execute().data[0]
    wing_id = user_data['wing_id']

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_quiz':
            question = request.form['question']
            quiz_type = request.form['quiz_type']
            options = [request.form.get(f'option_{i}') for i in range(1, int(quiz_type[0]) + 1)]
            correct_option = int(request.form['correct_option']) - 1

            quiz_response = supabase.table('quizzes').insert({
                "question": question,
                "quiz_type": quiz_type,
                "wing_id": wing_id,
                "creator_id": user_data['id']
            }).execute()
            quiz_id = quiz_response.data[0]['id']

            for i, option_text in enumerate(options):
                supabase.table('quiz_options').insert({
                    "quiz_id": quiz_id,
                    "option_text": option_text,
                    "is_correct": i == correct_option
                }).execute()
            flash("Quiz created!", "success")

        elif action == 'send_notification':
            content = request.form['notification_content']
            supabase.table('notifications').insert({
                "content": content,
                "wing_id": wing_id,
                "sender_id": user_data['id']
            }).execute()
            flash("Notification sent!", "success")

        elif action == 'submit_learning':
            learning_text = request.form['learning_text']
            supabase.table('learnings').insert({
                "username": username,
                "wing_id": wing_id,
                "role": "winghead",
                "learning_text": learning_text
            }).execute()
            flash("Learning updated!", "success")

    learnings = supabase.table('learnings').select('username, learning_text').eq('wing_id', wing_id).execute().data or []
    quizzes = supabase.table('quizzes').select('id, question, quiz_type').eq('wing_id', wing_id).eq('creator_id', user_data['id']).execute().data or []
    notifications = supabase.table('notifications').select('id, content, sent_at').eq('wing_id', wing_id).order('sent_at', desc=True).limit(5).execute().data or []

    selected_quiz_id = request.args.get('quiz_id')
    responses = []
    if selected_quiz_id:
        responses = supabase.table('quiz_responses').select('user_id, selected_option_id, text_response').eq('quiz_id', selected_quiz_id).execute().data or []
        for r in responses:
            r['username'] = supabase.table('users').select('username').eq('id', r['user_id']).execute().data[0]['username']
            if r['selected_option_id']:
                option = supabase.table('quiz_options').select('option_text, is_correct').eq('id', r['selected_option_id']).execute().data[0]
                r['option_text'] = option['option_text']
                r['is_correct'] = option['is_correct']

    return render_template('winghead_dashboard.html', learnings=learnings, user=user_data, quizzes=quizzes, 
                          responses=responses, selected_quiz_id=selected_quiz_id, notifications=notifications)

@app.route('/admin_view_learnings', methods=['GET', 'POST'])
def admin_view_learnings():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    wings = supabase.table('wings').select('*').execute().data or []
    selected_wing = request.form.get('wing_id')
    learnings = []

    if selected_wing:
        learnings = supabase.table('learnings').select('role, username, learning_text').eq('wing_id', selected_wing).execute().data or []

    return render_template('admin_view_learnings.html', wings=wings, learnings=learnings)

@app.route('/special_admin_view_learnings', methods=['GET', 'POST'])
def special_admin_view_learnings():
    if 'username' not in session or session['role'] != 'special_admin':
        return redirect(url_for('login'))

    wings = supabase.table('wings').select('*').execute().data or []
    selected_wing = request.form.get('wing_id')
    learnings = []

    if selected_wing:
        learnings = supabase.table('learnings').select('id, role, username, learning_text').eq('wing_id', selected_wing).execute().data or []

    if request.method == 'POST' and 'delete_learning_id' in request.form:
        learning_id = request.form['delete_learning_id']
        supabase.table('learnings').delete().eq('id', learning_id).execute()
        flash('Learning response deleted!', 'danger')
        return redirect(url_for('special_admin_view_learnings'))

    return render_template('special_admin_view_learnings.html', wings=wings, learnings=learnings)

if __name__ == '__main__':
    app.run(debug=True)