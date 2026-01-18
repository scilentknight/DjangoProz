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


# Another Way
# from orders.models import OrderProduct
# from store.models import Product
# from mlxtend.frequent_patterns import apriori, association_rules
# import pandas as pd

# def get_apriori_recommendations(user, cart_product_ids, min_support=0.5, min_confidence=0.75):
#     """
#     Generate personalized product recommendations based on the Apriori algorithm
#     using only the current user's previous order history.

#     Parameters:
#     - user: the current authenticated user
#     - cart_product_ids: list of product IDs currently in the user's cart
#     - min_support: minimum support threshold for frequent itemsets
#     - min_confidence: minimum confidence threshold for association rules

#     Returns:
#     - QuerySet of recommended Product objects
#     """

#     if not user.is_authenticated:
#         return Product.objects.none()  # Only recommend for logged-in users

#     # Ensure cart_product_ids are integers
#     cart_product_ids = list(map(int, cart_product_ids))

#     # -----------------------------
#     # 1. Collect User Transaction Data
#     # -----------------------------
#     orders = OrderProduct.objects.filter(order__user=user).values('order_id', 'product_id')
#     if not orders.exists():
#         return Product.objects.none()  # User has no previous orders

#     # -----------------------------
#     # 2. Convert orders to DataFrame
#     # -----------------------------
#     df = pd.DataFrame(list(orders))

#     # -----------------------------
#     # 3. Create basket format for Apriori
#     # -----------------------------
#     basket = df.groupby(['order_id', 'product_id']).size().unstack(fill_value=0)
#     basket = basket.applymap(lambda x: 1 if x > 0 else 0)

#     # -----------------------------
#     # 4. Identify Frequent Itemsets
#     # -----------------------------
#     frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)
#     if frequent_itemsets.empty:
#         return Product.objects.none()  # No frequent combinations

#     # -----------------------------
#     # 5. Generate Association Rules
#     # -----------------------------
#     rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
#     if rules.empty:
#         return Product.objects.none()  # No rules meet threshold

#     # -----------------------------
#     # 6. Recommend Products Based on Current Cart
#     # -----------------------------
#     recommended_ids = set()
#     for _, rule in rules.iterrows():
#         antecedents = set(map(int, rule['antecedents']))
#         consequents = set(map(int, rule['consequents']))

#         if antecedents.intersection(cart_product_ids):
#             recommended_ids.update(consequents)

#     # Remove products already in the cart
#     recommended_ids.difference_update(cart_product_ids)

#     # Return as Django QuerySet
#     return Product.objects.filter(id__in=recommended_ids)







