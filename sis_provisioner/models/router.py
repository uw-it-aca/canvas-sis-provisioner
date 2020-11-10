class AnalyticsRouter:
    def db_for_read(self, model, **hints):
        """
        Attempts to read canvas_analytics models go to analytics db.
        """
        if model._meta.app_label == 'canvas_analytics':
            return 'analytics'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write canvas_analytics models go to analytics db.
        """
        if model._meta.app_label == 'canvas_analytics':
            return 'analytics'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Only relations within the same db are allowed.
        """
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the canvas_analytics app only appears in the analytics db.
        """
        if app_label == 'canvas_analytics':
            return db == 'analytics'
        return None
