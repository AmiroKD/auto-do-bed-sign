from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required

from ..models import db, User
from ..crypto import encrypt_password
from ..scheduler import add_user_job, remove_user_job, update_user_job


users_bp = Blueprint('users', __name__)

CRON_PRESETS = {
    '10 9 * * *': '每天 09:10（北京时间）',
    '30 9 * * *': '每天 09:30（北京时间）',
    '10 10 * * *': '每天 10:10（北京时间）',
    '30 10 * * *': '每天 10:30（北京时间）',
}


@users_bp.route('/')
@login_required
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users/list.html', users=users)


@users_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def user_new():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('账号和密码为必填项', 'danger')
            return render_template('users/form.html', presets=CRON_PRESETS, user=None)

        user = User(
            username=username,
            password_encrypted=encrypt_password(password),
            principal=request.form.get('principal', '').strip() or None,
            credential=request.form.get('credential', '').strip() or None,
            email=request.form.get('email', '').strip() or None,
            enabled='enabled' in request.form,
        )
        valid_presets = set(CRON_PRESETS.keys())
        cron_times = [t for t in request.form.getlist('cron_times') if t in valid_presets]
        if not cron_times:
            flash('请至少选择一个打卡时间', 'danger')
            return render_template('users/form.html', presets=CRON_PRESETS, user=None)
        user.set_cron_times(cron_times)
        db.session.add(user)
        db.session.commit()

        if user.enabled:
            add_user_job(user)

        flash(f'用户 {username} 添加成功', 'success')
        return redirect(url_for('users.user_list'))

    return render_template('users/form.html', presets=CRON_PRESETS, user=None)


@users_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username:
            flash('账号为必填项', 'danger')
            return render_template('users/form.html', presets=CRON_PRESETS, user=user)

        user.username = username
        if password:
            user.password_encrypted = encrypt_password(password)
        user.principal = request.form.get('principal', '').strip() or None
        user.credential = request.form.get('credential', '').strip() or None
        user.email = request.form.get('email', '').strip() or None
        valid_presets = set(CRON_PRESETS.keys())
        cron_times = [t for t in request.form.getlist('cron_times') if t in valid_presets]
        if not cron_times:
            flash('请至少选择一个打卡时间', 'danger')
            return render_template('users/form.html', presets=CRON_PRESETS, user=user)
        user.set_cron_times(cron_times)
        user.enabled = 'enabled' in request.form
        db.session.commit()

        update_user_job(user)

        flash(f'用户 {username} 更新成功', 'success')
        return redirect(url_for('users.user_list'))

    return render_template('users/form.html', presets=CRON_PRESETS, user=user)


@users_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    username = user.username
    remove_user_job(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'用户 {username} 已删除', 'success')
    return redirect(url_for('users.user_list'))


@users_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    user.enabled = not user.enabled
    db.session.commit()

    update_user_job(user)

    status = '启用' if user.enabled else '禁用'
    flash(f'用户 {user.username} 已{status}', 'success')
    return redirect(url_for('users.user_list'))


@users_bp.route('/users/<int:user_id>/test', methods=['POST'])
@login_required
def user_test(user_id):
    """立即执行查寝测试，返回 JSON 结果"""
    from flask import jsonify
    user = User.query.get_or_404(user_id)
    from ..crypto import decrypt_password
    from ..tasks.gotobed import run_gotobed

    password = decrypt_password(user.password_encrypted)
    result = run_gotobed(
        username=user.username,
        password=password,
        principal=user.principal,
        credential=user.credential,
        email=user.email,
    )

    # 记录日志
    from ..models import Log
    log = Log(user_id=user.id, status=result['status'], message=result['message'])
    db.session.add(log)
    db.session.commit()

    return jsonify(result)
