import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
_jobs = {}  # user_id -> job_id
_app = None  # 保存 app 引用


def _execute_gotobed(user_id: int):
    """调度任务回调：执行指定用户的查寝"""
    from .models import db, User, Log
    from .tasks.gotobed import run_gotobed
    from .crypto import decrypt_password

    if _app is None:
        logger.error('Flask app 未初始化')
        return

    with _app.app_context():
        user = db.session.get(User, user_id)
        if not user or not user.enabled:
            logger.warning(f'用户 {user_id} 不存在或已禁用，跳过')
            return

        password = decrypt_password(user.password_encrypted)

        result = run_gotobed(
            username=user.username,
            password=password,
            principal=user.principal,
            credential=user.credential,
            email=user.email,
        )

        log = Log(
            user_id=user.id,
            status=result['status'],
            message=result['message'],
        )
        db.session.add(log)
        db.session.commit()
        logger.info(f'用户 {user.username} 查寝完成: {result["status"]}')


def add_user_job(user):
    """为用户添加调度任务"""
    job_id = f'gotobed_{user.id}'
    try:
        trigger = CronTrigger.from_crontab(user.cron_expr, timezone='Asia/Shanghai')
        scheduler.add_job(
            _execute_gotobed,
            trigger=trigger,
            args=[user.id],
            id=job_id,
            replace_existing=True,
            max_instances=1,
        )
        _jobs[user.id] = job_id
        logger.info(f'已添加调度: 用户 {user.username}, cron={user.cron_expr}')
    except Exception as e:
        logger.error(f'添加调度失败: 用户 {user.username}, 错误: {e}')


def remove_user_job(user_id: int):
    """移除用户的调度任务"""
    job_id = _jobs.pop(user_id, None)
    if job_id:
        try:
            scheduler.remove_job(job_id)
            logger.info(f'已移除调度: 用户ID {user_id}')
        except Exception:
            pass


def update_user_job(user):
    """更新用户的调度任务（删除旧的，添加新的）"""
    remove_user_job(user.id)
    if user.enabled:
        add_user_job(user)


def init_scheduler(app):
    """初始化调度器，加载所有启用的用户"""
    global _app
    _app = app

    with app.app_context():
        from .models import User
        users = User.query.filter_by(enabled=True).all()
        for user in users:
            add_user_job(user)

    scheduler.start()
    logger.info(f'调度器已启动，共加载 {len(users)} 个用户任务')
