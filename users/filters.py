# users/filters.py

import django_filters
from django.db.models import Q
from .models import Product, Room, Style, Color
from functools import reduce
import operator


class ProductFilter(django_filters.FilterSet):
    """
    Backend-friendly filter that accepts common frontend param names:
      - q (text search)
      - category (id)
      - subcategory (id)
      - price_min, price_max
      - rooms, styles, colors as comma-separated id lists
      - is_on_sale
      - rating lookups via rating, rating__gte, rating__lte
    """

    # free-text aliases (frontend may send `q` or `search`)
    q = django_filters.CharFilter(method='filter_q')
    search = django_filters.CharFilter(method='filter_q')

    # IDs are more stable for frontend usage
    category = django_filters.CharFilter(method='filter_category')
    subcategory = django_filters.NumberFilter(field_name='subcategory__id', lookup_expr='exact')

    # Price friendly names (support multiple aliases used by frontends)
    price_min = django_filters.NumberFilter(field_name='original_price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='original_price', lookup_expr='lte')
    # aliases
    priceFrom = django_filters.NumberFilter(field_name='original_price', lookup_expr='gte')
    priceTo = django_filters.NumberFilter(field_name='original_price', lookup_expr='lte')
    from_ = django_filters.NumberFilter(field_name='original_price', lookup_expr='gte', label='from')
    to = django_filters.NumberFilter(field_name='original_price', lookup_expr='lte')

    # Boolean
    is_on_sale = django_filters.BooleanFilter()

    # Comma-separated lists for related object ids (frontend-friendly)
    rooms = django_filters.CharFilter(method='filter_rooms')
    styles = django_filters.CharFilter(method='filter_styles')
    colors = django_filters.CharFilter(method='filter_colors')
    
    # Rating filter with OR logic for multiple values
    rating = django_filters.CharFilter(method='filter_rating')

    def _split_parts(self, value):
        """Return a list of parts (strings) from csv or repeated params."""
        # Some clients send repeated query params (GET list) and some send CSV.
        if value is None:
            return []
        parts = []
        if isinstance(value, (list, tuple)):
            for v in value:
                parts += [p.strip() for p in str(v).split(',') if p.strip() != '']
            return parts
        # If a Django request is available on the filterset, try to read repeated params
        # using getlist() which is how QueryDict exposes repeated params.
        try:
            req = getattr(self, 'request', None)
            if req is not None:
                # safe: QueryDict.getlist will return [] if not present
                qlist = req.GET.getlist
                if callable(qlist):
                    listed = qlist(value)
                    if listed:
                        for v in listed:
                            parts += [p.strip() for p in str(v).split(',') if p.strip() != '']
                        return parts
        except Exception:
            # ignore any request-related oddities and fall back to value parsing
            pass

        parts = [p.strip() for p in str(value).split(',') if p.strip() != '']
        return parts

    def _classify_parts(self, parts):
        """Classify parts into ints and strings; decode %23 to # for hex codes."""
        ints = []
        strs = []
        for p in parts:
            if p is None:
                continue
            # normalize encoding of hash (#)
            if isinstance(p, str) and p.startswith('%23'):
                p = p.replace('%23', '#')
            # trim and preserve original for classification
            if isinstance(p, str):
                p = p.strip()
            try:
                ints.append(int(p))
            except Exception:
                # treat everything else as string; normalize to lowercase for name matching
                if isinstance(p, str):
                    strs.append(p.strip())
                else:
                    strs.append(str(p))
        return ints, strs

    def filter_rooms(self, queryset, name, value):
        # prefer request.getlist(name) when available to support repeated params
        parts = []
        req = getattr(self, 'request', None)
        if req is not None:
            listed = req.GET.getlist(name)
            if listed:
                parts = self._split_parts(listed)
        if not parts:
            parts = self._split_parts(value)
        ids, strs = self._classify_parts(parts)
        q = queryset
        if ids:
            q = q.filter(rooms__id__in=ids)
        if strs:
            # build an ORed Q(...) for case-insensitive exact matches
            qname = None
            for s in strs:
                q_cond = Q(rooms__name__icontains=s)
                qname = q_cond if qname is None else (qname | q_cond)
            if qname is not None:
                q = q.filter(qname)
        return q.distinct()

    def filter_styles(self, queryset, name, value):
        parts = []
        req = getattr(self, 'request', None)
        if req is not None:
            listed = req.GET.getlist(name)
            if listed:
                parts = self._split_parts(listed)
        if not parts:
            parts = self._split_parts(value)
        ids, strs = self._classify_parts(parts)
        q = queryset
        if ids:
            q = q.filter(styles__id__in=ids)
        if strs:
            qname = None
            for s in strs:
                q_cond = Q(styles__name__icontains=s)
                qname = q_cond if qname is None else (qname | q_cond)
            if qname is not None:
                q = q.filter(qname)
        return q.distinct()

    def filter_colors(self, queryset, name, value):
        parts = []
        req = getattr(self, 'request', None)
        if req is not None:
            listed = req.GET.getlist(name)
            if listed:
                parts = self._split_parts(listed)
        if not parts:
            parts = self._split_parts(value)
        ids, strs = self._classify_parts(parts)
        q = queryset
        if ids:
            q = q.filter(colors__id__in=ids)
        if strs:
            # classify as hex (starts with #) or names (case-insensitive)
            hexes = [s for s in strs if isinstance(s, str) and s.startswith('#')]
            names = [s for s in strs if not (isinstance(s, str) and s.startswith('#'))]
            if hexes:
                qhex = None
                for h in hexes:
                    q_cond = Q(colors__hex_code__iexact=h)
                    qhex = q_cond if qhex is None else (qhex | q_cond)
                if qhex is not None:
                    q = q.filter(qhex)
            if names:
                qname = None
                for n in names:
                    q_cond = Q(colors__name__icontains=n)
                    qname = q_cond if qname is None else (qname | q_cond)
                if qname is not None:
                    q = q.filter(qname)
        return q.distinct()

    # frontend may send material as a filter; map to styles (name or id)
    material = django_filters.CharFilter(method='filter_material')

    def filter_material(self, queryset, name, value):
        parts = []
        req = getattr(self, 'request', None)
        if req is not None:
            listed = req.GET.getlist(name)
            if listed:
                parts = self._split_parts(listed)
        if not parts:
            parts = self._split_parts(value)
        ids, strs = self._classify_parts(parts)
        q = queryset
        if ids:
            q = q.filter(styles__id__in=ids)
        if strs:
            qname = None
            for s in strs:
                q_cond = Q(styles__name__icontains=s)
                qname = q_cond if qname is None else (qname | q_cond)
            if qname is not None:
                q = q.filter(qname)
        return q.distinct()

    def filter_q(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(short_description__icontains=value) |
            Q(description__icontains=value)
        )

    def filter_category(self, queryset, name, value):
        """Filter by category IDs (comma-separated string or single ID)"""
        if not value:
            return queryset
        
        # Handle comma-separated category IDs
        category_ids = []
        if isinstance(value, str):
            category_ids = [int(id.strip()) for id in value.split(',') if id.strip().isdigit()]
        elif isinstance(value, (list, tuple)):
            category_ids = [int(id) for id in value if str(id).isdigit()]
        else:
            try:
                category_ids = [int(value)]
            except (ValueError, TypeError):
                return queryset
        
        if category_ids:
            return queryset.filter(category__id__in=category_ids)
        
        return queryset

    def filter_rating(self, queryset, name, value):
        """Filter by rating values (comma-separated string or single value)"""
        if not value:
            return queryset
        
        # Handle comma-separated rating values
        rating_values = []
        if isinstance(value, str):
            rating_values = [float(rating.strip()) for rating in value.split(',') if rating.strip().replace('.', '').isdigit()]
        elif isinstance(value, (list, tuple)):
            rating_values = [float(rating) for rating in value if str(rating).replace('.', '').isdigit()]
        else:
            try:
                rating_values = [float(value)]
            except (ValueError, TypeError):
                return queryset
        
        if rating_values:
            # Use OR logic for multiple ratings
            from django.db.models import Q
            q_objects = Q()
            for rating in rating_values:
                q_objects |= Q(rating=rating)
            return queryset.filter(q_objects)
        
        return queryset

    class Meta:
        model = Product
        # keep numeric lookups for backward compatibility
        fields = {
            'original_price': ['exact', 'gte', 'lte'],
        }