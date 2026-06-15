from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
import re

from ..models import db, User
from ..crypto import encrypt_password
from ..scheduler import add_user_job, remove_user_job, update_user_job


users_bp = Blueprint('users', __name__)

CRON_PRESETS = {
    '10 21 * * *': '每天 21:10（北京时间）',
    '30 21 * * *': '每天 21:30（北京时间）',
    '10 22 * * *': '每天 22:10（北京时间）',
    '30 22 * * *': '每天 22:30（北京时间）',
}


def _validate_cron_time(expr: str) -> bool:
    """验证 cron 表达式格式：分 时 * * *（0-59 0-23）"""
    m = re.match(r'^(\d{1,2}) (\d{1,2}) \* \* \*$', expr.strip())
    if not m:
        return False
    minute, hour = int(m.group(1)), int(m.group(2))
    return 0 <= minute <= 59 and 0 <= hour <= 23


def _parse_cron_times(form) -> list:
    """从表单解析所有打卡时间（预设 + 自定义）"""
    times = form.getlist('cron_times')
    custom = form.get('custom_time', '').strip()
    if custom:
        # 自定义时间格式 HH:MM -> cron 表达式
        match = re.match(r'^(\d{1,2}):(\d{2})$', custom)
        if match:
            h, m = match.group(1), match.group(2)
            times.append(f'{m} {h} * * *')
    # 去重 + 验证
    valid = []
    seen = set()
    for t in times:
        t = t.strip()
        if t not in seen and _validate_cron_time(t):
            valid.append(t)
            seen.add(t)
    return valid


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
        cron_times = _parse_cron_times(request.form)
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
        cron_times = _parse_cron_times(request.form)
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
