class BackendDatabaseRouter:
    """将只读运维模型固定路由到 FastAPI 使用的业务数据库。"""

    app_label = "ops"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return "backend"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return "backend"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        labels = {obj1._meta.app_label, obj2._meta.app_label}
        if self.app_label in labels:
            return labels == {self.app_label}
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "backend" or app_label == self.app_label:
            return False
        return None
