
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date

from .models import Projects
from employees.models import Employees


def project_to_dict(project):
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "employee_id": project.employee_id,
        "employee_name": (
            project.employee.name
            if project.employee_id
            else project.employee_name
        ),
        "start_date": (
            project.start_date.isoformat()
            if project.start_date else None
        ),
        "finish_date": (
            project.finish_date.isoformat()
            if project.finish_date else None
        ),
        "status": project.status,
    }


@csrf_exempt
def project_list(request):

    if request.method == "GET":
        projects = Projects.objects.all().order_by("id")
        return JsonResponse(
            [project_to_dict(p) for p in projects],
            safe=False
        )

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            start_value = data.get("start_date")
            finish_value = data.get("finish_date")

            start_date = (
                parse_date(start_value) if start_value else None
            )
            finish_date = (
                parse_date(finish_value) if finish_value else None
            )

            if start_value and start_date is None:
                return JsonResponse({
                    "error": "Invalid start_date. Use YYYY-MM-DD."
                }, status=400)

            if finish_value and finish_date is None:
                return JsonResponse({
                    "error": "Invalid finish_date. Use YYYY-MM-DD."
                }, status=400)

            project = Projects(
                name=data["name"],
                description=data.get("description", ""),
                status=data["status"],
                employee_name=data.get("employee_name", ""),
                start_date=start_date,
                finish_date=finish_date,
            )

            employee_id = data.get("employee_id")

            if employee_id:
                project.employee = Employees.objects.get(id=employee_id)

                if not project.employee_name:
                    project.employee_name = project.employee.name

            project.save()

            return JsonResponse({
                "message": "Project created successfully",
                "project": project_to_dict(project),
            }, status=201)

        except Employees.DoesNotExist:
            return JsonResponse({
                "error": "Employee not found"
            }, status=404)

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return JsonResponse({
                "error": "Invalid JSON or required fields are missing"
            }, status=400)

    return JsonResponse({
        "error": "Method not allowed"
    }, status=405)


@csrf_exempt
def project_detail(request, project_id):

    try:
        project = Projects.objects.get(id=project_id)
    except Projects.DoesNotExist:
        return JsonResponse({
            "error": "Project not found"
        }, status=404)

    if request.method == "GET":
        return JsonResponse(project_to_dict(project))

    if request.method == "PUT":
        try:
            data = json.loads(request.body)

            project.name = data.get("name", project.name)
            project.description = data.get(
                "description", project.description
            )
            project.status = data.get("status", project.status)
            project.employee_name = data.get(
                "employee_name", project.employee_name
            )

            if "start_date" in data:
                value = data["start_date"]
                parsed_date = parse_date(value) if value else None

                if value and parsed_date is None:
                    return JsonResponse({
                        "error": "Invalid start_date. Use YYYY-MM-DD."
                    }, status=400)

                project.start_date = parsed_date

            if "finish_date" in data:
                value = data["finish_date"]
                parsed_date = parse_date(value) if value else None

                if value and parsed_date is None:
                    return JsonResponse({
                        "error": "Invalid finish_date. Use YYYY-MM-DD."
                    }, status=400)

                project.finish_date = parsed_date

            if "employee_id" in data:
                if data["employee_id"]:
                    project.employee = Employees.objects.get(
                        id=data["employee_id"]
                    )

                    if "employee_name" not in data:
                        project.employee_name = project.employee.name
                else:
                    project.employee = None

            project.save()

            return JsonResponse({
                "message": "Project updated successfully",
                "project": project_to_dict(project),
            })

        except Employees.DoesNotExist:
            return JsonResponse({
                "error": "Employee not found"
            }, status=404)

        except (json.JSONDecodeError, TypeError, ValueError):
            return JsonResponse({
                "error": "Invalid JSON or required fields are missing"
            }, status=400)

    if request.method == "DELETE":
        project.delete()
        return JsonResponse({
            "message": "Project deleted successfully"
        })

    return JsonResponse({
        "error": "Method not allowed"
    }, status=405)


def employee_projects(request, employee_id):

    if request.method != "GET":
        return JsonResponse({
            "error": "Method not allowed"
        }, status=405)

    try:
        employee = Employees.objects.get(id=employee_id)
    except Employees.DoesNotExist:
        return JsonResponse({
            "error": "Employee not found"
        }, status=404)

    projects = Projects.objects.filter(
        employee_id=employee.id
    ).order_by("id")

    return JsonResponse({
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "designation": employee.designation,
        },
        "count": projects.count(),
        "projects": [project_to_dict(p) for p in projects],
    })
