"""OpenAI + Pinecone RAG — Unified CLI entry point.

Usage:
    python main.py --ingest --namespace my-project
    python main.py --query "What happened?" --namespace my-project
    python main.py --help
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI + Pinecone RAG Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --ingest --namespace my-project
  python main.py --query "Find documents about AI" --namespace my-project
  python main.py --ingest --query "Search after ingest" --namespace my-project
        """,
    )
    parser.add_argument("--ingest", action="store_true", help="Run ingestion pipeline")
    parser.add_argument("--query", "-q", type=str, help="Query text for search")
    parser.add_argument("--namespace", default="default", help="Pinecone namespace")
    parser.add_argument("--data-dir", default="data", help="Data directory for ingestion")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results for query")

    args = parser.parse_args()

    if not args.ingest and not args.query:
        parser.print_help()
        sys.exit(0)

    if args.ingest:
        from ingest import ingest
        ingest(namespace=args.namespace, data_dir=args.data_dir)

    if args.query:
        from query import query
        query(query_text=args.query, namespace=args.namespace, top_k=args.top_k)


if __name__ == "__main__":
    main()
