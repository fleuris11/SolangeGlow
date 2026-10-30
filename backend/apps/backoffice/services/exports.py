"""« Export as CSV » on every list of the admin: the columns of the list, the rows chosen
(or all the rows of the filter), readable by Excel, written in the audit journal."""

from __future__ import annotations

import csv

from django.contrib import admin
from django.contrib.admin.utils import label_for_field, lookup_field
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from apps.core.audit.services import record
from apps.core.selectors import get_setting


def _value(model_admin, obj, field) -> str:
    try:
        _f, _attr, value = lookup_field(field, obj, model_admin)
    except Exception:  # a column that cannot be read for this row stays empty
        return ""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if hasattr(value, "all") and callable(value.all):
        return ", ".join(str(item) for item in value.all())
    return strip_tags(str(value))


def can_export(request) -> bool:
    user = request.user
    return user.is_superuser or user.has_perm("backoffice.export_csv")


@admin.action(description=_("Export as CSV"))
def export_csv(model_admin, request, queryset):
    if not can_export(request):
        raise PermissionDenied
    fields = [f for f in model_admin.get_list_display(request) if f != "action_checkbox"]
    meta = model_admin.model._meta
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    response["Content-Disposition"] = f'attachment; filename="{meta.model_name}-{stamp}.csv"'
    response.write("﻿")  # Excel reads the accents
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [strip_tags(str(label_for_field(f, model_admin.model, model_admin))) for f in fields]
    )
    count = 0
    most = int(get_setting("backoffice.export_max_rows", default=50_000))
    for obj in queryset[:most]:
        writer.writerow([_value(model_admin, obj, f) for f in fields])
        count += 1
    record(
        "backoffice.exported",
        None,
        actor=request.user,
        metadata={"model": meta.label, "rows": count},
    )
    return response
