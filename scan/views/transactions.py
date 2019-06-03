from django.db.models import Q
from django.views.generic import ListView

from burst.multiout import MultiOutPack
from java_wallet.models import Transaction
from scan.caching_paginator import CachingPaginator
from scan.helpers import get_account_name, get_txs_count, get_last_height
from scan.models import MultiOut
from scan.views.base import IntSlugDetailView


class TxListView(ListView):
    model = Transaction
    queryset = Transaction.objects.using('java_wallet').all()
    template_name = 'txs/list.html'
    context_object_name = 'txs'
    paginator_class = CachingPaginator
    paginate_by = 25
    ordering = '-height'

    def get_queryset(self):
        qs = super().get_queryset()

        if self.request.GET.get('block'):
            qs = qs.filter(block__height=self.request.GET.get('block'))

        elif self.request.GET.get('a'):
            qs = qs.filter(
                Q(sender_id=self.request.GET.get('a')) | Q(recipient_id=self.request.GET.get('a'))
            )

        else:
            qs = qs[:100000]

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        obj = context[self.context_object_name]

        for t in obj:
            t.sender_name = get_account_name(t.sender_id)
            if t.recipient_id:
                t.recipient_name = get_account_name(t.recipient_id)

            if t.type == 0 and t.subtype in {1, 2}:
                v, t.multiout = MultiOutPack().unpack_header(t.attachment_bytes)

        context['txs_cnt'] = get_txs_count()

        return context


class TxDetailView(IntSlugDetailView):
    model = Transaction
    queryset = Transaction.objects.using('java_wallet').all()
    template_name = 'txs/detail.html'
    context_object_name = 'tx'
    slug_field = 'id'
    slug_url_kwarg = 'id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        obj = context[self.context_object_name]

        context['blocks_confirm'] = get_last_height() - obj.height

        context['sender_name'] = get_account_name(obj.sender_id)
        if context[self.context_object_name].recipient_id:
            context['recipient_name'] = get_account_name(obj.recipient_id)

        if obj.type == 0 and obj.subtype in {1, 2}:
            v, obj.multiout = MultiOutPack().unpack_header(obj.attachment_bytes)
            obj.recipients = MultiOut.objects.filter(tx_id=obj.id).all()

        return context