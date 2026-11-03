"""Prints the demo objects the screen captures need (run with manage.py shell)."""

import json

from apps.academy.models import Course, Lesson
from apps.messaging.models import ConversationMember
from apps.payments.models import Payment
from apps.selection_france.models import SelectionOrder, SelectionProduct
from apps.shop.models import Order, Product
from apps.social.models import Post

order = Order.objects.select_related("buyer").order_by("-created_at").first()
buyer = order.buyer if order else None
course = Course.objects.filter(status="published").first()
lesson = Lesson.objects.filter(module__course=course).first() if course else None
product = Product.objects.filter(status="published").select_related("pro").first()
membership = ConversationMember.objects.filter(user=buyer).first() if buyer else None

print(
    "CAPTUREIDS"
    + json.dumps(
        {
            "client_phone": str(buyer.phone) if buyer and buyer.phone else "",
            "post": str(getattr(Post.objects.filter(status="published").first(), "pk", "")),
            "order": str(getattr(order, "pk", "")),
            "payment": str(getattr(Payment.objects.filter(buyer=buyer).first(), "pk", "")),
            "course": getattr(course, "slug", ""),
            "lesson": str(getattr(lesson, "pk", "")),
            "selection": getattr(SelectionProduct.objects.first(), "slug", ""),
            "selection_order": str(getattr(SelectionOrder.objects.first(), "pk", "")),
            "conversation": str(getattr(membership, "conversation_id", "")),
            "pro": product.pro.slug if product else "",
            "product": product.slug if product else "",
        }
    )
)
