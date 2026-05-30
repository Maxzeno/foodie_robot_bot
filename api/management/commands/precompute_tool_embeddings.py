from django.core.management.base import BaseCommand
from api.services.ai.tool_definitions import get_tool_definitions
from api.services.ai.embedding_filter import ToolEmbeddingFilter


class Command(BaseCommand):
    help = 'Precompute and cache embeddings for all AI tools'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting tool embedding precomputation...'))

        try:
            # Get all tool definitions
            all_tools = get_tool_definitions()
            self.stdout.write(f'Found {len(all_tools)} tools to process')

            # Initialize the embedding filter
            embedding_filter = ToolEmbeddingFilter()

            # Precompute and cache all embeddings
            embedding_filter.precompute_tool_embeddings(all_tools)

            self.stdout.write(self.style.SUCCESS(
                f'Successfully cached embeddings for {len(all_tools)} tools!'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
