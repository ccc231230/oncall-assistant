import logging
from pathlib import Path
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from app.core.config import settings
from app.core.html_parser import parse_html

logger = logging.getLogger(__name__)

INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "smartcn": {
                    "type": "smartcn",
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "smartcn", "search_analyzer": "smartcn"},
            "content": {"type": "text", "analyzer": "smartcn", "search_analyzer": "smartcn"},
        }
    },
}


class ESClient:
    def __init__(self):
        self.es = AsyncElasticsearch(settings.ES_HOST)

    async def create_index(self) -> None:
        """Create index if it doesn't exist."""
        exists = await self.es.indices.exists(index=settings.ES_INDEX)
        if not exists:
            await self.es.indices.create(index=settings.ES_INDEX, body=INDEX_MAPPING)
            logger.info(f"Created index: {settings.ES_INDEX}")

    async def index_document(self, doc_id: str, title: str, content: str) -> None:
        """Index a single document."""
        await self.es.index(
            index=settings.ES_INDEX,
            id=doc_id,
            body={"id": doc_id, "title": title, "content": content},
            refresh=True,
        )

    async def index_all_from_data(self, data_dir: Path) -> int:
        """Index all SOP HTML files from the data directory. Returns count of indexed docs."""
        count = 0
        actions = []
        for filepath in sorted(data_dir.glob("*.html")):
            doc_id = filepath.stem
            html = filepath.read_text(encoding="utf-8")
            parsed = parse_html(html)
            actions.append(
                {
                    "_index": settings.ES_INDEX,
                    "_id": doc_id,
                    "_source": {
                        "id": doc_id,
                        "title": parsed["title"],
                        "content": parsed["content"],
                    },
                }
            )
            count += 1

        if actions:
            success, errors = await async_bulk(self.es, actions, refresh=True)
            logger.info(f"Indexed {success} documents, errors: {len(errors)}")

        return count

    async def search(self, query: str, size: int = 10) -> dict:
        """Search documents by keyword query. Returns {query, results}."""
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content"],
                    "type": "best_fields",
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "content": {
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"],
                        "number_of_fragments": 1,
                        "fragment_size": 200,
                    },
                }
            },
            "size": size,
        }

        resp = await self.es.search(index=settings.ES_INDEX, body=body)

        results = []
        for hit in resp["hits"]["hits"]:
            source = hit["_source"]

            # Build snippet from highlight or fallback to content
            snippet = ""
            if "highlight" in hit:
                if "content" in hit["highlight"]:
                    snippet = hit["highlight"]["content"][0]
                elif "title" in hit["highlight"]:
                    snippet = hit["highlight"]["title"][0]
            if not snippet:
                snippet = source.get("content", "")[:200]

            results.append(
                {
                    "id": source["id"],
                    "title": source["title"],
                    "snippet": snippet,
                    "score": hit["_score"] or 1.0,
                }
            )

        return {"query": query, "results": results}

    async def close(self) -> None:
        """Close the ES client connection."""
        await self.es.close()
