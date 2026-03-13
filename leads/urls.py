from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    path("", views.lead_list, name="lead_list"),
    path("leads/add/", views.lead_create, name="lead_create"),
    path("leads/<str:lead_id>/", views.lead_detail, name="lead_detail"),
    path("import/", views.import_csv, name="import_csv"),
    path("kanban/", views.kanban_board, name="kanban_board"),
    path("reports/funnel/", views.funnel_report, name="funnel_report"),
]

