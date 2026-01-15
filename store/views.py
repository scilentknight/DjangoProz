from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ReviewRating, ProductGallery, Category # this category should be remove
from category.models import Category
from carts.models import CartItem
from django.db.models import Q

from carts.views import _cart_id
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from .forms import ReviewForm
from django.contrib import messages
from orders.models import OrderProduct


# def store(request, category_slug=None):
#     categories = None
#     products = None

#     if category_slug != None:
#         categories = get_object_or_404(Category, slug=category_slug)
#         products = Product.objects.filter(category=categories, is_available=True)
#         paginator = Paginator(products, 1)
#         page = request.GET.get('page')
#         paged_products = paginator.get_page(page)
#         product_count = products.count()
#     else:
#         products = Product.objects.all().filter(is_available=True).order_by('id')
#         paginator = Paginator(products, 6)
#         page = request.GET.get('page')
#         paged_products = paginator.get_page(page)
#         product_count = products.count()

#     context = {
#         'products': paged_products,
#         'product_count': product_count,
#     }
#     return render(request, 'store/store.html', context)

# def store(request):
#     products = Product.objects.all()
#     categories = request.GET.getlist('category')  # list of category ids
#     sizes = request.GET.getlist('size')          # list of sizes
#     min_price = request.GET.get('min_price')
#     max_price = request.GET.get('max_price')

#     # Filter by category
#     if categories:
#         products = products.filter(category_id__in=categories)
    
#     # Filter by size through Variation
#     if sizes:
#         products = products.filter(
#             variation__variation_category='size',
#             variation__variation_value__in=sizes
#         ).distinct()
    
#     # Filter by price
#     if min_price:
#         products = products.filter(price__gte=min_price)
    
#     if max_price:
#         products = products.filter(price__lte=max_price)
    
#     context = {
#         'products': products,
#         'links': Category.objects.all(),
#     }
#     return render(request, 'store/store.html', context)

def store(request, category_slug=None):
    products = Product.objects.filter(is_available=True)
    categories = None

    # -----------------------------
    # URL-based category filtering
    # -----------------------------
    if category_slug:
        categories = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=categories)

    # -----------------------------
    # GET-based filters
    # -----------------------------
    category_ids = request.GET.getlist('category')  # category ids
    sizes = request.GET.getlist('size')              # sizes
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Filter by category (checkbox/filter UI)
    if category_ids:
        products = products.filter(category_id__in=category_ids)

    # Filter by size through Variation
    if sizes:
        products = products.filter(
            variation__variation_category='size',
            variation__variation_value__in=sizes
        ).distinct()

    # Filter by price
    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    # -----------------------------
    # Pagination
    # -----------------------------
    paginator = Paginator(products, 6)
    page = request.GET.get('page')
    paged_products = paginator.get_page(page)

    # -----------------------------
    # Context
    # -----------------------------
    context = {
        'products': paged_products,
        'product_count': products.count(),
        'links': Category.objects.all(),
        'selected_category': categories,
    }

    return render(request, 'store/store.html', context)



def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e

    if request.user.is_authenticated:
        try:
            orderproduct = OrderProduct.objects.filter(user=request.user, product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            orderproduct = None
    else:
        orderproduct = None

    # Get the reviews
    reviews = ReviewRating.objects.filter(product_id=single_product.id, status=True)

    # Get the product gallery
    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)

    context = {
        'single_product': single_product,
        'in_cart'       : in_cart,
        'orderproduct': orderproduct,
        'reviews': reviews,
        'product_gallery': product_gallery,
    }
    return render(request, 'store/product_detail.html', context)


def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user__id=request.user.id, product__id=product_id)
            form = ReviewForm(request.POST, instance=reviews)
            form.save()
            messages.success(request, 'Thank you! Your review has been updated.')
            return redirect(url)
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.ip = request.META.get('REMOTE_ADDR')
                data.product_id = product_id
                data.user_id = request.user.id
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
                return redirect(url)
