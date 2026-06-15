import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
_jobs = {}  # user_id -> [job_id1, job_id2, ...]  一个用户可有多个定时任务
_app = None  # 保存 app 引用

BJT = ZoneInfo('Asia/Shanghai')


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


def _cleanup_old_logs():
    """清理 5 天前的执行日志"""
    from .models import db, Log

    if _app is None:
        logger.error('Flask app 未初始化')
        return

    with _app.app_context():
        cutoff = datetime.now(BJT).replace(tzinfo=None) - timedelta(days=5)
        count = Log.query.filter(Log.executed_at < cutoff).delete()
        db.session.commit()
        if count > 0:
            logger.info(f'已清理 {count} 条过期日志（{cutoff.strftime("%Y-%m-%d %H:%M")} 之前）')


def add_user_job(user):
    """为用户添加调度任务（支持多个时间）"""
    job_ids = []
    for idx, cron_expr in enumerate(user.get_cron_times()):
        job_id = f'gotobed_{user.id}_{idx}'
        try:
            trigger = CronTrigger.from_crontab(cron_expr, timezone='Asia/Shanghai')
            scheduler.add_job(
                _execute_gotobed,
                trigger=trigger,
                args=[user.id],
                id=job_id,
                replace_existing=True,
                max_instances=1,
            )
            job_ids.append(job_id)
            logger.info(f'已添加调度: 用户 {user.username}, cron={cron_expr}')
        except Exception as e:
            logger.error(f'添加调度失败: 用户 {user.username}, cron={cron_expr}, 错误: {e}')
    _jobs[user.id] = job_ids


def remove_user_job(user_id: int):
    """移除用户的所有调度任务"""
    job_ids = _jobs.pop(user_id, [])
    for job_id in job_ids:
        try:
            scheduler.remove_job(job_id)
            logger.info(f'已移除调度: {job_id}')
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

    # 每天凌晨 4 点清理 5 天前的日志
    scheduler.add_job(
        _cleanup_old_logs,
        trigger=CronTrigger(hour=4, minute=0, timezone='Asia/Shanghai'),
        id='cleanup_old_logs',
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f'调度器已启动，共加载 {len(users)} 个用户任务')
