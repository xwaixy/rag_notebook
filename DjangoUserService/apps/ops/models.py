from django.db import models


class ChatSession(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    user_id = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(db_column="metadata", blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "chat_sessions"
        verbose_name = "会话"
        verbose_name_plural = "会话"

    def __str__(self):
        return self.title or self.id


class ChatMessage(models.Model):
    id = models.IntegerField(primary_key=True)
    session_id = models.CharField(max_length=64, db_index=True)
    role = models.CharField(max_length=32)
    content = models.TextField()
    metadata = models.JSONField(db_column="metadata", blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "chat_messages"
        verbose_name = "会话消息"
        verbose_name_plural = "会话消息"

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class Note(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user_id = models.CharField(max_length=36, db_index=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    tags = models.JSONField(blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "notes"
        verbose_name = "笔记"
        verbose_name_plural = "笔记"

    def __str__(self):
        return self.title


class ReviewRecord(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    note_id = models.CharField(max_length=36, db_index=True)
    user_id = models.CharField(max_length=36, db_index=True)
    last_reviewed_at = models.DateTimeField(blank=True, null=True)
    review_count = models.IntegerField(default=0)
    next_review_at = models.DateTimeField(blank=True, null=True)
    interval_days = models.IntegerField(default=1)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "review_records"
        verbose_name = "回顾记录"
        verbose_name_plural = "回顾记录"

    def __str__(self):
        return f"{self.user_id} / {self.note_id}"
