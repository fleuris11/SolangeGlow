from rest_framework import serializers

from .models import Trade


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ["key", "name", "icon"]
