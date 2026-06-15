from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required
from .. import login_manager

auth_bp = Blueprint('auth', __name__)


class AdminUser:
    """管理员虚拟用户，仅用密码认证"""

    def __init__(self):
        self.id = 1

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    if user_id == '1':
        return AdminUser()
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == current_app.config['ADMIN_PASSWORD']:
            login_user(AdminUser())
            next_page = request.args.get('next')
            return redirect(next_page or url_for('users.user_list'))
        flash('密码错误', 'danger')
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
