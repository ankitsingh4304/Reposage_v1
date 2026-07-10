from __future__ import annotations

import argparse
import sys


def _print_answer(answer) -> None:
    print("\n" + answer.text + "\n")
    if answer.sources:
        print("Sources:")
        for hit in answer.sources:
            print(f"  [{hit.score:.2f}] {hit.chunk.citation()}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chat_with_repo")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Index a repo (local path or git URL)")
    p_ingest.add_argument("source")
    p_ingest.add_argument("--no-reset", action="store_true",
                          help="Add to the existing index instead of rebuilding")

    p_ask = sub.add_parser("ask", help="Ask a single question")
    p_ask.add_argument("question")
    p_ask.add_argument("-k", type=int, default=None)
    p_ask.add_argument("--agentic", action="store_true", help="Use the self-correcting agent")

    sub.add_parser("chat", help="Interactive question loop")

    p_eval = sub.add_parser("eval", help="Run a labeled eval set and report retrieval metrics")
    p_eval.add_argument("eval_set")
    p_eval.add_argument("--label", default="run")
    p_eval.add_argument("--compare", default=None)
    p_eval.add_argument("-k", type=int, default=10)
    p_eval.add_argument("--agentic", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "eval":
        from eval.harness import run_cli

        run_cli(args.eval_set, label=args.label, retrieve_k=args.k, compare_to=args.compare,
                agentic=args.agentic)
        return 0

    from src.pipeline.rag import RAGPipeline

    pipeline = RAGPipeline()

    if args.command == "ingest":
        pipeline.ingest(args.source, reset=not args.no_reset)
        return 0

    if args.command == "ask":
        try:
            if args.agentic:
                ans = pipeline.answer_agentic(args.question)
                if ans.trace:
                    print(f"[agent: {ans.trace.get('rewrites', 0)} query rewrite(s)]")
                _print_answer(ans)
            else:
                _print_answer(pipeline.answer(args.question, k=args.k))
        except Exception as e:
            print(f"\nLLM call failed: {type(e).__name__}: {e}")
            print("Free tiers throttle transiently — retry, or switch LLM_PROVIDER in .env.\n")
            return 1
        return 0

    if args.command == "chat":
        print("Ask questions about the indexed codebase. Ctrl-C or 'exit' to quit.\n")
        while True:
            try:
                q = input("you > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if q.lower() in {"exit", "quit"}:
                return 0
            if q:
                _print_answer(pipeline.answer(q))

    return 0


if __name__ == "__main__":
    sys.exit(main())
