from django.db import migrations, models

from posthog.migration_helpers import CreateIndexConcurrently


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("posthog", "1394_backfill_secret_tokens_to_psak"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="userintegration",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(kind="anthropic_api_key"),
                        fields=("user",),
                        name="unique_anthropic_api_key_user_integration",
                    ),
                ),
            ],
            database_operations=[
                CreateIndexConcurrently(
                    index_name="unique_anthropic_api_key_user_integration",
                    table_name="posthog_user_integration",
                    columns='("user_id")',
                    unique=True,
                    where="WHERE kind = 'anthropic_api_key'",
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="userintegration",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(kind="openai_api_key"),
                        fields=("user",),
                        name="unique_openai_api_key_user_integration",
                    ),
                ),
            ],
            database_operations=[
                CreateIndexConcurrently(
                    index_name="unique_openai_api_key_user_integration",
                    table_name="posthog_user_integration",
                    columns='("user_id")',
                    unique=True,
                    where="WHERE kind = 'openai_api_key'",
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="userintegration",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(kind="claude_subscription"),
                        fields=("user",),
                        name="unique_claude_subscription_user_integration",
                    ),
                ),
            ],
            database_operations=[
                CreateIndexConcurrently(
                    index_name="unique_claude_subscription_user_integration",
                    table_name="posthog_user_integration",
                    columns='("user_id")',
                    unique=True,
                    where="WHERE kind = 'claude_subscription'",
                ),
            ],
        ),
    ]
