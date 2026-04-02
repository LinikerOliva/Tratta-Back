"""
trathea_core/utils/pagination.py
Paginação padronizada para toda a API Trathea.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class TratheaPagination(PageNumberPagination):
    """
    Paginação padrão Trathea.
    Mantém o formato {"success", "data", "message", "errors"}.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "data": {
                "results": data,
                "pagination": {
                    "count": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "current_page": self.page.number,
                    "page_size": self.page_size,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            },
            "message": "Listagem retornada com sucesso.",
            "errors": [],
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {
                    "type": "object",
                    "properties": {
                        "results": schema,
                        "pagination": {
                            "type": "object",
                            "properties": {
                                "count": {"type": "integer"},
                                "total_pages": {"type": "integer"},
                                "current_page": {"type": "integer"},
                                "next": {"type": "string", "nullable": True},
                                "previous": {"type": "string", "nullable": True},
                            },
                        },
                    },
                },
                "message": {"type": "string"},
                "errors": {"type": "array"},
            },
        }
