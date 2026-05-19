from decimal import Decimal

from django.utils import timezone

from .models import ComboOffer


def evaluate_combo_offers(items_list):
    """
    Evaluates list of order items against active ComboOffers and returns the best matched offer and its discount.

    items_list format:
    [
        {
            "product_id": int,
            "category_id": int or None,
            "sub_category_id": int or None,
            "quantity": int,
            "price": Decimal (item unit price)
        },
        ...
    ]
    """
    now = timezone.now()
    active_combos = ComboOffer.objects.filter(
        is_active=True, start_date__lte=now, end_date__gte=now
    ).prefetch_related("products", "categories", "sub_categories")

    if not active_combos.exists() or not items_list:
        return None, Decimal("0.00")

    best_offer = None
    best_discount = Decimal("0.00")

    # Helper maps for cart lookup
    cart_product_quantities = {}
    cart_product_prices = {}
    cart_items_by_product = {}

    for item in items_list:
        p_id = item["product_id"]
        qty = item["quantity"]
        price = Decimal(str(item["price"]))

        cart_product_quantities[p_id] = cart_product_quantities.get(p_id, 0) + qty
        cart_product_prices[p_id] = price
        cart_items_by_product[p_id] = item

    for offer in active_combos:
        # Check rule conditions
        has_products = offer.products.exists()
        has_categories = offer.categories.exists()
        has_subcategories = offer.sub_categories.exists()

        # If it has no conditions, skip
        if not (has_products or has_categories or has_subcategories):
            continue

        is_match = False
        matching_subtotal = Decimal("0.00")
        matching_quantity = 0

        if has_products:
            # Product Bundle: All listed products must be present in the cart
            required_product_ids = set(offer.products.values_list("id", flat=True))
            cart_product_ids = set(cart_product_quantities.keys())

            # Check if all required products are in the cart
            if required_product_ids.issubset(cart_product_ids):
                # Check if each required product meets min_quantity or the aggregate quantity is met
                # By default, a bundle requires at least 1 of each product
                all_have_min_qty = all(
                    cart_product_quantities[pid] >= 1 for pid in required_product_ids
                )
                total_qty = sum(
                    cart_product_quantities[pid] for pid in required_product_ids
                )

                if all_have_min_qty and total_qty >= offer.min_quantity:
                    is_match = True
                    # Calculate subtotal for the required products (up to the matched bundle sets)
                    # Let's find how many full bundle sets we have in the cart
                    num_sets = min(
                        cart_product_quantities[pid] for pid in required_product_ids
                    )

                    for pid in required_product_ids:
                        # We apply discount to the items that form the combo/bundle
                        matching_subtotal += cart_product_prices[pid] * num_sets
                        matching_quantity += num_sets

        elif has_categories:
            # Category bulk rule: minimum total quantity of items from those categories
            required_category_ids = set(offer.categories.values_list("id", flat=True))

            matching_items = []
            for item in items_list:
                if item.get("category_id") in required_category_ids:
                    matching_items.append(item)

            total_cat_qty = sum(item["quantity"] for item in matching_items)
            if total_cat_qty >= offer.min_quantity:
                is_match = True
                for item in matching_items:
                    matching_subtotal += Decimal(str(item["price"])) * item["quantity"]
                    matching_quantity += item["quantity"]

        elif has_subcategories:
            # Subcategory bulk rule
            required_subcategory_ids = set(
                offer.sub_categories.values_list("id", flat=True)
            )

            matching_items = []
            for item in items_list:
                if item.get("sub_category_id") in required_subcategory_ids:
                    matching_items.append(item)

            total_subcat_qty = sum(item["quantity"] for item in matching_items)
            if total_subcat_qty >= offer.min_quantity:
                is_match = True
                for item in matching_items:
                    matching_subtotal += Decimal(str(item["price"])) * item["quantity"]
                    matching_quantity += item["quantity"]

        # Calculate discount for this matched offer
        if is_match:
            discount = Decimal("0.00")
            if offer.offer_type == "percentage":
                discount = matching_subtotal * (
                    offer.discount_value / Decimal("100.00")
                )
            elif offer.offer_type == "fixed":
                discount = offer.discount_value
            elif offer.offer_type == "bundle_price":
                if (
                    offer.bundle_price is not None
                    and matching_subtotal > offer.bundle_price
                ):
                    # Discount is the difference between normal subtotal and the fixed bundle price
                    # E.g. Buy A + B (worth 12000) for 10000 -> discount = 2000
                    discount = matching_subtotal - offer.bundle_price

            # Ensure discount is positive and doesn't exceed matching subtotal
            discount = max(Decimal("0.00"), min(discount, matching_subtotal))

            # Pick the best offer (highest discount value)
            if discount > best_discount:
                best_discount = discount
                best_offer = offer

    return best_offer, best_discount
