from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from horilla_core.models import HorillaUser
from horilla_core.signals import company_currency_changed
from horilla_crm.accounts.models import Account
from horilla_keys.models import ShortcutKey

# Define your accounts signals here


@receiver(post_save, sender=HorillaUser)
def create_account_shortcuts(sender, instance, created, **kwargs):
    predefined = [
        {"page": "/accounts/accounts-view/", "key": "A", "command": "alt"},
    ]

    for item in predefined:
        if not ShortcutKey.objects.filter(user=instance, page=item["page"]).exists():
            ShortcutKey.objects.create(
                user=instance,
                page=item["page"],
                key=item["key"],
                command=item["command"],
                company=instance.company,
            )


@receiver(company_currency_changed)
def update_accounts_on_currency_change(sender, **kwargs):
    """
    Update Account currency fields (like annual_revenue) when a company's currency changes.
    """
    company = kwargs.get("company")
    conversion_rate = kwargs.get("conversion_rate")

    accounts_to_update = []

    # Assuming Account has a ForeignKey to company, else adjust filtering accordingly
    accounts = Account.objects.filter(company=company).only("id", "annual_revenue")

    for account in accounts:
        needs_update = False

        if account.annual_revenue is not None:
            account.annual_revenue *= conversion_rate
            needs_update = True

        if needs_update:
            accounts_to_update.append(account)

    if accounts_to_update:
        Account.objects.bulk_update(
            accounts_to_update, ["annual_revenue"], batch_size=1000
        )
