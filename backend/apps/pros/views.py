from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .selectors import active_trades
from .serializers import TradeSerializer


class TradeListView(APIView):
    """Trades offered at sign-up and in search, in the language of the request."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["catalogue"], responses=TradeSerializer(many=True))
    def get(self, request):
        return Response(TradeSerializer(active_trades(), many=True).data)
