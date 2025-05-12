from django import template
from datetime import datetime, timedelta
import re

register = template.Library()

@register.filter
def strip_html(value):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', value)

@register.filter
def orderby(queryset, field):
    return queryset.order_by(field)


@register.filter
def is_warning(change_request):
    """
    Checks if the requiredbydate is not null, targetdate is null, 
    and createddate is more than 14 days ago.
    """
    try:
        # Ensure createddate is a datetime object
        if change_request.createddate:
            if isinstance(change_request.createddate, datetime):
                created_date = change_request.createddate
            else:
                # Convert `date` to `datetime`
                created_date = datetime.combine(change_request.createddate, datetime.min.time())
            
            # Calculate the difference in days
            days_difference = (datetime.now() - created_date).days
            
            # Apply the condition
            return (
                change_request.requiredbydate is not None and
                change_request.targetdate is None and
                days_difference > 14
            )
    except AttributeError:
        # Handle cases where attributes are missing
        return False
    return False

@register.filter
def is_targetdate_warning(change_request):
    """
    Checks if targetdate is greater than requiredbydate. Does nothing if requiredbydate is null.
    Any associated Feature's targetdate is greater than ChangeRequest.targetdate.
    """
    try:
        # Check if ChangeRequest.targetdate is greater than ChangeRequest.requiredbydate
        if change_request.targetdate and change_request.requiredbydate:
            if change_request.targetdate > change_request.requiredbydate:
                return True

        # Check if any associated Feature's targetdate is greater than ChangeRequest.targetdate
        if change_request.targetdate:
            for feature in change_request.features.all():
                if feature.targetdate and feature.targetdate > change_request.targetdate:
                    return True

    except AttributeError:
        # Handle cases where attributes are missing
        return False

    return False

@register.filter
def is_feature_targetdate_warning(feature, change_request):
    """
    Checks if the Feature targetdate is greater than the ChangeRequest targetdate.
    """
    try:
        if feature.targetdate and change_request.targetdate:
            return feature.targetdate > change_request.targetdate
    except AttributeError:
        # Handle cases where attributes are missing
        return False
    return False