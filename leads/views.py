from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from django.db.models import Count, Sum, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CsvImportForm, LeadForm, StatusChangeForm
from .models import Lead, LeadStatusHistory, Manager, PipelineStatus


def lead_list(request: HttpRequest) -> HttpResponse:
    search = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    leads_qs = Lead.objects.select_related("manager", "current_status")

    if search:
        leads_qs = leads_qs.filter(Q(lead_id__icontains=search) | Q(source__icontains=search))

    if status_filter:
        leads_qs = leads_qs.filter(current_status__status_id=status_filter)

    total_leads = leads_qs.count()
    active_leads = leads_qs.filter(current_status__status_id__lt=4).count()
    total_amount = leads_qs.aggregate(total=Sum("amount"))["total"] or 0

    statuses = PipelineStatus.objects.all()

    context: dict[str, Any] = {
        "leads": leads_qs.order_by("-created_at"),
        "search": search,
        "status_filter": status_filter,
        "statuses": statuses,
        "total_leads": total_leads,
        "active_leads": active_leads,
        "total_amount": total_amount,
    }
    return render(request, "leads/lead_list.html", context)


def lead_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save()
            LeadStatusHistory.objects.create(
                lead=lead,
                status=lead.current_status,
                changed_by=lead.manager,
                comment="Создание лида",
            )
            return redirect("leads:lead_detail", lead_id=lead.lead_id)
    else:
        form = LeadForm()

    return render(request, "leads/lead_form.html", {"form": form})


def lead_detail(request: HttpRequest, lead_id: str) -> HttpResponse:
    lead = get_object_or_404(Lead.objects.select_related("manager", "current_status"), pk=lead_id)

    if request.method == "POST":
        form = StatusChangeForm(request.POST)
        if form.is_valid():
            new_status: PipelineStatus = form.cleaned_data["status"]
            changed_by: Manager = form.cleaned_data["changed_by"]
            comment: str = form.cleaned_data["comment"]

            status_changed = lead.current_status != new_status
            if status_changed:
                lead.current_status = new_status
                lead.save(update_fields=["current_status", "updated_at"])

            # Всегда пишем запись в историю, даже если статус не изменился,
            # чтобы фиксировать комментарий и факт действия пользователя.
            LeadStatusHistory.objects.create(
                lead=lead,
                status=new_status,
                changed_by=changed_by,
                comment=comment,
            )
            return redirect("leads:lead_detail", lead_id=lead.lead_id)
    else:
        form = StatusChangeForm(
            initial={
                "status": lead.current_status_id,
                "changed_by": lead.manager_id,
            }
        )

    history = lead.status_history.select_related("status", "changed_by").all()

    return render(
        request,
        "leads/lead_detail.html",
        {
            "lead": lead,
            "form": form,
            "history": history,
        },
    )


def import_csv(request: HttpRequest) -> HttpResponse:
    errors: list[str] = []
    created = 0
    updated = 0

    if request.method == "POST":
        form = CsvImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            try:
                data = file.read().decode("utf-8")
            except UnicodeDecodeError:
                errors.append("Не удалось прочитать файл как UTF-8.")
            else:
                buf = io.StringIO(data)
                sniffer = csv.Sniffer()
                sample = data[:1024]
                dialect = sniffer.sniff(sample, delimiters=",;")
                reader = csv.DictReader(buf, dialect=dialect)

                required_fields = {
                    "lead_id",
                    "created_at",
                    "source",
                    "manager_id",
                    "current_status_id",
                    "amount",
                    "updated_at",
                }
                if not required_fields.issubset(reader.fieldnames or []):
                    errors.append("Некорректные заголовки CSV. Ожидаются: " + ", ".join(sorted(required_fields)))
                else:
                    for row in reader:
                        try:
                            manager, _ = Manager.objects.get_or_create(
                                manager_id=row["manager_id"],
                                defaults={"name": row["manager_id"]},
                            )
                            status = PipelineStatus.objects.get(status_id=int(row["current_status_id"]))
                            created_at = datetime.fromisoformat(row["created_at"])
                            updated_at = datetime.fromisoformat(row["updated_at"])
                            amount = float(row["amount"])
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"Строка с lead_id={row.get('lead_id')}: {exc}")
                            continue

                        lead, is_created = Lead.objects.update_or_create(
                            lead_id=row["lead_id"],
                            defaults={
                                "created_at": created_at,
                                "source": row["source"],
                                "manager": manager,
                                "current_status": status,
                                "amount": amount,
                                "updated_at": updated_at,
                            },
                        )
                        if is_created:
                            created += 1
                        else:
                            updated += 1

            return render(
                request,
                "leads/import_csv.html",
                {"form": form, "errors": errors, "created": created, "updated": updated},
            )
    else:
        form = CsvImportForm()

    return render(request, "leads/import_csv.html", {"form": form, "errors": errors, "created": created, "updated": updated})


def kanban_board(request: HttpRequest) -> HttpResponse:
    columns: list[dict[str, Any]] = []
    for status in PipelineStatus.objects.all():
        leads = (
            Lead.objects.filter(current_status=status)
            .select_related("manager", "current_status")
            .order_by("-created_at")
        )
        columns.append({"status": status, "leads": leads})

    return render(request, "leads/kanban.html", {"columns": columns})


def funnel_report(request: HttpRequest) -> HttpResponse:
    statuses = list(PipelineStatus.objects.order_by("stage_order"))
    leads = list(Lead.objects.all())

    history = LeadStatusHistory.objects.select_related("status", "lead").order_by("lead_id", "changed_at")

    # вычисляем среднюю длительность нахождения в каждом статусе
    durations: dict[int, list[float]] = {s.status_id: [] for s in statuses}

    per_lead_history: dict[str, list[LeadStatusHistory]] = {}
    for h in history:
        per_lead_history.setdefault(h.lead.lead_id, []).append(h)

    for lead_id, changes in per_lead_history.items():
        for idx, h in enumerate(changes):
            start = h.changed_at
            if idx + 1 < len(changes):
                end = changes[idx + 1].changed_at
            else:
                end = datetime.now(tz=start.tzinfo)
            delta_days = (end - start).total_seconds() / 86400
            durations.setdefault(h.status.status_id, []).append(delta_days)

    report_rows: list[dict[str, Any]] = []
    leads_by_status = Lead.objects.values("current_status").annotate(count=Count("lead_id"), total_amount=Sum("amount"))
    agg_map = {row["current_status"]: row for row in leads_by_status}

    for status in statuses:
        agg = agg_map.get(status.status_id, {})
        count = agg.get("count", 0) or 0
        total_amount = agg.get("total_amount", 0) or 0
        dur_list = durations.get(status.status_id, [])
        avg_duration = sum(dur_list) / len(dur_list) if dur_list else 0
        report_rows.append(
            {
                "status": status,
                "count": count,
                "total_amount": total_amount,
                "avg_duration": avg_duration,
            }
        )

    # конверсия между этапами: простое отношение количества текущих лидов на этапе к количеству на предыдущем
    for idx, row in enumerate(report_rows):
        if idx == 0:
            row["conversion"] = 100.0
        else:
            prev_count = report_rows[idx - 1]["count"]
            row["conversion"] = (row["count"] / prev_count * 100.0) if prev_count else 0.0

    return render(request, "leads/funnel_report.html", {"rows": report_rows})

