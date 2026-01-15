from orders.models import OrderProduct
from store.models import Product
from mlxtend.frequent_patterns import apriori, association_rules
import pandas as pd

def get_apriori_recommendations(cart_product_ids, min_support=0.01):
    """
    Get product recommendations based on Apriori algorithm
    using previous order history.
    
    cart_product_ids: list of product IDs currently in cart
    """

    # 1. Fetch all completed orders
    orders = OrderProduct.objects.values('order_id', 'product_id')

    if not orders.exists():
        return Product.objects.none()  # no recommendations

    # 2. Convert orders to dataframe
    df = pd.DataFrame(list(orders))

    # 3. Create a basket for Apriori
    basket = (df.groupby(['order_id', 'product_id'])
                .size().unstack(fill_value=0))

    # Convert quantities to 1 (existence)
    basket = basket.applymap(lambda x: 1 if x > 0 else 0)

    # 4. Apply Apriori
    frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)

    if frequent_itemsets.empty:
        return Product.objects.none()

    # 5. Generate rules
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)

    # 6. Get recommended products based on current cart
    recommended_ids = set()
    for _, rule in rules.iterrows():
        if set(rule['antecedents']).intersection(cart_product_ids):
            recommended_ids.update(rule['consequents'])

    # Remove products already in cart
    recommended_ids = recommended_ids.difference(cart_product_ids)

    return Product.objects.filter(id__in=recommended_ids)

# # Another Way
# import pandas as pd
# from mlxtend.frequent_patterns import apriori, association_rules
# from orders.models import OrderProduct
# from store.models import Product


# def get_apriori_recommendations(cart_product_ids, limit=6):
#     """
#     cart_product_ids → list of product IDs currently in cart
#     """

#     # 1. Build transactions from past orders
#     order_products = OrderProduct.objects.filter(ordered=True)

#     transactions = {}
#     for item in order_products:
#         transactions.setdefault(item.order_id, set()).add(item.product_id)

#     transactions = list(transactions.values())

#     # If not enough data, stop
#     if len(transactions) < 5:
#         return Product.objects.none()

#     # 2. One-hot encoding
#     all_products = Product.objects.values_list('id', flat=True)

#     encoded = []
#     for transaction in transactions:
#         encoded.append({pid: (pid in transaction) for pid in all_products})

#     df = pd.DataFrame(encoded)

#     # 3. Apriori algorithm
#     frequent_itemsets = apriori(
#         df,
#         min_support=0.02,
#         use_colnames=True
#     )

#     if frequent_itemsets.empty:
#         return Product.objects.none()

#     rules = association_rules(
#         frequent_itemsets,
#         metric="lift",
#         min_threshold=1
#     )

#     # 4. Generate recommendations
#     recommendations = set()

#     for _, rule in rules.iterrows():
#         antecedents = set(rule['antecedents'])
#         consequents = set(rule['consequents'])

#         if antecedents.intersection(cart_product_ids):
#             recommendations.update(consequents)

#     # Remove cart items
#     recommendations -= set(cart_product_ids)

#     return Product.objects.filter(id__in=recommendations)[:limit]