from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from store.models import Product
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import datetime
import json
import requests

# Create your views here.

# =========================
# KHALTI CONFIG
# =========================
KHALTI_SECRET_KEY = "8924c55a0f0d495cb6e576e77027c269"
KHALTI_INIT_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"


# # Khalti Test Secret Key from test-admin.khalti.com
# KHALTI_SECRET_KEY = "8924c55a0f0d495cb6e576e77027c269"
# KHALTI_INIT_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"
# KHALTI_LOOKUP_URL = "https://dev.khalti.com/api/v2/epayment/lookup/"
# KHALTI_VERIFY_URL = "https://dev.khalti.com/api/v2/payment/verify/"


# =========================
# INITIATE PAYMENT
# =========================
def payments(request):
    if request.method == "POST":
        data = json.loads(request.body)
        order_number = data.get("orderID")
        amount = int(data.get("amount"))  # in paisa

        order = Order.objects.get(order_number=order_number, is_ordered=False)

        payload = {
            "return_url": request.build_absolute_uri('/orders/order_complete/'),
            "website_url": request.build_absolute_uri('/'),
            "amount": amount,
            "purchase_order_id": order_number,
            "purchase_order_name": f"Order {order_number}",
            "customer_info": {
                "name": f"{order.first_name} {order.last_name}",
                "email": order.email,
                "phone": order.phone,
            }
        }

        headers = {
            "Authorization": f"Key {KHALTI_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(KHALTI_INIT_URL, json=payload, headers=headers)
        return JsonResponse(response.json())


# =========================
# PLACE ORDER
# =========================
def place_order(request, total=0, quantity=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)

    if cart_items.count() == 0:
        return redirect('store')

    tax = 0
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
        quantity += cart_item.quantity

    tax = (1 * total) / 100
    grand_total = total + tax

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                user=current_user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone=form.cleaned_data['phone'],
                email=form.cleaned_data['email'],
                address_line_1=form.cleaned_data['address_line_1'],
                address_line_2=form.cleaned_data['address_line_2'],
                country=form.cleaned_data['country'],
                state=form.cleaned_data['state'],
                city=form.cleaned_data['city'],
                order_note=form.cleaned_data['order_note'],
                order_total=grand_total,
                tax=tax,
                ip=request.META.get('REMOTE_ADDR'),
            )

            current_date = datetime.date.today().strftime("%Y%m%d")
            order.order_number = current_date + str(order.id)
            order.save()

            context = {
                "order": order,
                "cart_items": cart_items,
                "total": total,
                "tax": tax,
                "grand_total": grand_total,
            }
            return render(request, "orders/payments.html", context)

    return redirect("checkout")


# =========================
# ORDER COMPLETE
# =========================
def order_complete(request):
    order_number = request.GET.get("purchase_order_id")
    transaction_id = request.GET.get("transaction_id") or request.GET.get("txnId")
    payment_method = request.GET.get("payment_method", "Khalti")
    amount = request.GET.get("total_amount")

    if not order_number:
        return redirect("home")

    order = Order.objects.filter(order_number=order_number).first()
    if not order:
        return HttpResponse("Order not found", status=400)

    # If already processed
    if order.is_ordered:
        ordered_products = OrderProduct.objects.filter(order=order)
        subtotal = sum(i.product_price * i.quantity for i in ordered_products)

        return render(request, "orders/order_complete.html", {
            "order": order,
            "payment": order.payment,
            "ordered_products": ordered_products,
            "order_number": order.order_number,
            "transID": order.payment.payment_id if order.payment else "COD",
            "subtotal": subtotal,
        })

    # Create payment
    payment = Payment.objects.create(
        user=order.user,
        payment_id=transaction_id or "COD",
        payment_method=payment_method,
        amount_paid=float(amount) / 100 if amount else order.order_total,
        status="Completed",
    )

    # Update order
    order.payment = payment
    order.is_ordered = True
    order.status = "Completed"
    order.save()

    # Move cart items to OrderProduct
    cart_items = CartItem.objects.filter(user=order.user)

    for item in cart_items:
        order_product = OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=order.user,
            product=item.product,
            quantity=item.quantity,
            product_price=item.product.price,
            ordered=True,
        )
        order_product.variations.set(item.variations.all())

        # Reduce stock
        item.product.stock -= item.quantity
        item.product.save()

    cart_items.delete()

    # =========================
    # SEND ORDER CONFIRMATION EMAIL
    # =========================
    mail_subject = "Thank you for your order!"
    message = render_to_string("orders/order_received_email.html", {
        "user": order.user,
        "order": order,
    })
    EmailMessage(mail_subject, message, to=[order.email]).send()

    ordered_products = OrderProduct.objects.filter(order=order)
    subtotal = sum(i.product_price * i.quantity for i in ordered_products)

    return render(request, "orders/order_complete.html", {
        "order": order,
        "payment": payment,
        "ordered_products": ordered_products,
        "order_number": order.order_number,
        "transID": payment.payment_id,
        "subtotal": subtotal,
    })
