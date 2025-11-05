def allow_inactive_subscription(view_or_class):
    """
    Mark a view or view class as exempt from subscription checks.
    Works for both function-based and class-based views.
    """
    if hasattr(view_or_class, "as_view"):
        # Class-based view
        view_or_class.allow_inactive_subscription = True
        original_as_view = view_or_class.as_view

        def new_as_view(*args, **kwargs):
            view = original_as_view(*args, **kwargs)
            view.allow_inactive_subscription = True
            return view

        view_or_class.as_view = new_as_view
        return view_or_class
    else:
        # Function-based view
        view_or_class.allow_inactive_subscription = True
        return view_or_class
