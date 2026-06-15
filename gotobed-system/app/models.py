from datetime import datetime, timezone, timedelta
import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 北京时间 UTC+8
_BJ_TZ = timezone(timedelta(hours=8))


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    principal = db.Column(db.Text, nullable=True)
    credential = db.Column(db.Text, nullable=True)
    email = db.Column(db.Text, nullable=True)
    cron_times = db.Column(db.Text, nullable=False, default='["10 21 * * *"]')
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(_BJ_TZ))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(_BJ_TZ),
                           onupdate=lambda: datetime.now(_BJ_TZ))

    logs = db.relationship('Log', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def get_cron_times(self) -> list:
        """获取 cron 时间列表"""
        try:
            return json.loads(self.cron_times)
        except (json.JSONDecodeError, TypeError):
            return ['10 21 * * *']

    def set_cron_times(self, times: list):
        """设置 cron 时间列表"""
        self.cron_times = json.dumps(times)

    def last_log(self):
        """获取最近一条执行日志"""
        return self.logs.order_by(Log.executed_at.desc()).first()

    def __repr__(self):
        return f'<User {self.username}>'


class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Text, nullable=False)  # 'success' / 'failure'
    message = db.Column(db.Text, nullable=False)
    executed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(_BJ_TZ))

    def __repr__(self):
        return f'<Log {self.id} {self.status}>'
