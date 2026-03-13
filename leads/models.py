from __future__ import annotations

from django.db import models


class Manager(models.Model):
    manager_id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Менеджер"
        verbose_name_plural = "Менеджеры"

    def __str__(self) -> str:
        return self.name


class PipelineStatus(models.Model):
    status_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    stage_order = models.IntegerField()
    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ["stage_order"]
        verbose_name = "Статус воронки"
        verbose_name_plural = "Статусы воронки"

    def __str__(self) -> str:
        return self.name


class Lead(models.Model):
    lead_id = models.CharField(primary_key=True, max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=255)
    manager = models.ForeignKey(Manager, on_delete=models.PROTECT)
    current_status = models.ForeignKey(PipelineStatus, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Лид"
        verbose_name_plural = "Лиды"

    def __str__(self) -> str:
        return self.lead_id


class LeadStatusHistory(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="status_history")
    status = models.ForeignKey(PipelineStatus, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(Manager, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "История статуса лида"
        verbose_name_plural = "История статусов лидов"

    def __str__(self) -> str:
        return f"{self.lead.lead_id} -> {self.status.name}"


